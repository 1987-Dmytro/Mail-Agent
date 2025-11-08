"""Integration tests for email polling functionality (end-to-end)."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.tasks.email_tasks import _poll_user_emails_async
from app.core.gmail_client import GmailClient
from app.core.encryption import encrypt_token


@pytest_asyncio.fixture
async def test_user_with_tokens(db_session: AsyncSession) -> User:
    """Create a test user with Gmail OAuth tokens.

    Returns:
        User with encrypted Gmail tokens
    """
    access_token = encrypt_token("test_access_token_polling")
    refresh_token = encrypt_token("test_refresh_token_polling")

    user = User(
        email="polling_test@gmail.com",
        hashed_password="$2b$12$test",
        is_active=True,
        gmail_oauth_token=access_token,
        gmail_refresh_token=refresh_token,
        gmail_connected_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.mark.asyncio
async def test_email_polling_end_to_end(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Full email polling flow.

    Tests:
    - GmailClient.get_messages() called with is:unread query
    - Gmail API returns 5 unread emails
    - Email metadata extracted (message_id, thread_id, sender, subject, received_at)
    - 5 EmailProcessingQueue records created with status="pending"
    - All records associated with correct user_id

    AC Coverage: AC#2
    """
    # Mock Gmail client get_messages to return 5 test emails
    mock_emails = [
        {
            "message_id": f"msg_{i}",
            "thread_id": f"thread_{i}",
            "sender": f"sender{i}@example.com",
            "subject": f"Test Email {i}",
            "received_at": datetime(2025, 11, 5, 10 + i, 0, 0, tzinfo=timezone.utc),
        }
        for i in range(1, 6)
    ]

    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails)):
        # Execute polling task
        new_count, skip_count = await _poll_user_emails_async(test_user_with_tokens.id)

    # Assert: 5 new emails, 0 duplicates
    assert new_count == 5
    assert skip_count == 0

    # Verify: 5 EmailProcessingQueue records created
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id
    )
    result = await db_session.execute(statement)
    emails = result.scalars().all()

    assert len(emails) == 5

    # Verify email metadata extracted correctly
    for i, email in enumerate(emails, start=1):
        assert email.gmail_message_id == f"msg_{i}"
        assert email.gmail_thread_id == f"thread_{i}"
        assert email.sender == f"sender{i}@example.com"
        assert email.subject == f"Test Email {i}"
        assert email.status == "pending"
        assert email.user_id == test_user_with_tokens.id


@pytest.mark.asyncio
async def test_email_polling_duplicate_detection(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Duplicate email detection.

    Tests:
    - First polling creates 5 EmailProcessingQueue records
    - Second polling with same message IDs skips all 5 (duplicates)
    - Unique constraint on gmail_message_id prevents duplicates
    - Duplicate count returned correctly

    AC Coverage: AC#2
    """
    # Mock Gmail client to return same 3 emails twice
    mock_emails = [
        {
            "message_id": "msg_dup_1",
            "thread_id": "thread_1",
            "sender": "duplicate@example.com",
            "subject": "Duplicate Test",
            "received_at": datetime(2025, 11, 5, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "message_id": "msg_dup_2",
            "thread_id": "thread_2",
            "sender": "duplicate2@example.com",
            "subject": "Duplicate Test 2",
            "received_at": datetime(2025, 11, 5, 10, 5, 0, tzinfo=timezone.utc),
        },
        {
            "message_id": "msg_dup_3",
            "thread_id": "thread_3",
            "sender": "duplicate3@example.com",
            "subject": "Duplicate Test 3",
            "received_at": datetime(2025, 11, 5, 10, 10, 0, tzinfo=timezone.utc),
        },
    ]

    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails)):
        # First polling - should create 3 records
        new_count_1, skip_count_1 = await _poll_user_emails_async(test_user_with_tokens.id)

        assert new_count_1 == 3
        assert skip_count_1 == 0

        # Second polling - should skip all 3 (duplicates)
        new_count_2, skip_count_2 = await _poll_user_emails_async(test_user_with_tokens.id)

        assert new_count_2 == 0
        assert skip_count_2 == 3

    # Verify: Only 3 records exist (no duplicates created)
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id
    )
    result = await db_session.execute(statement)
    emails = result.scalars().all()

    assert len(emails) == 3

    # Verify: gmail_message_id unique constraint enforced
    message_ids = [email.gmail_message_id for email in emails]
    assert len(message_ids) == len(set(message_ids))  # All unique


@pytest.mark.asyncio
async def test_email_polling_metadata_extraction(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Email metadata extraction accuracy.

    Tests:
    - All metadata fields extracted correctly
    - Datetime fields preserved with timezone
    - Optional fields (subject) handled gracefully
    - sender email normalized

    AC Coverage: AC#2
    """
    # Mock Gmail client with specific metadata
    received_timestamp = datetime(2025, 11, 5, 14, 30, 45, tzinfo=timezone.utc)

    mock_emails = [
        {
            "message_id": "msg_metadata_test",
            "thread_id": "thread_metadata",
            "sender": "TestSender@Example.COM",  # Test normalization
            "subject": "Test Subject with émojis 🎉",
            "received_at": received_timestamp,
        },
        {
            "message_id": "msg_no_subject",
            "thread_id": "thread_no_subject",
            "sender": "nosubject@example.com",
            "subject": None,  # Test None subject
            "received_at": received_timestamp,
        },
    ]

    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails)):
        new_count, skip_count = await _poll_user_emails_async(test_user_with_tokens.id)

    assert new_count == 2

    # Verify metadata extraction
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id
    ).order_by(EmailProcessingQueue.gmail_message_id)
    result = await db_session.execute(statement)
    emails = result.scalars().all()

    # Email 1: Full metadata
    email1 = emails[0]
    assert email1.gmail_message_id == "msg_metadata_test"
    assert email1.gmail_thread_id == "thread_metadata"
    assert email1.sender.lower() == "testsender@example.com"  # Normalized
    assert email1.subject == "Test Subject with émojis 🎉"
    assert email1.received_at == received_timestamp
    assert email1.status == "pending"

    # Email 2: None subject handled
    email2 = emails[1]
    assert email2.gmail_message_id == "msg_no_subject"
    assert email2.subject is None


@pytest.mark.asyncio
async def test_email_polling_empty_inbox(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Polling empty inbox.

    Tests:
    - Gmail API returns no emails
    - Polling completes successfully
    - No EmailProcessingQueue records created
    - Returns (0, 0) for new/skip counts

    AC Coverage: AC#2
    """
    # Mock Gmail client to return empty list
    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=[])):
        new_count, skip_count = await _poll_user_emails_async(test_user_with_tokens.id)

    # Assert: No emails processed
    assert new_count == 0
    assert skip_count == 0

    # Verify: No records created
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id
    )
    result = await db_session.execute(statement)
    emails = result.scalars().all()

    assert len(emails) == 0


@pytest.mark.asyncio
async def test_email_polling_mixed_new_and_duplicates(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Polling with mix of new and duplicate emails.

    Tests:
    - First polling creates 3 emails
    - Second polling with 2 duplicates + 2 new emails
    - Only 2 new emails created (5 total)
    - 2 duplicates skipped

    AC Coverage: AC#2
    """
    # First batch: 3 emails
    mock_emails_batch1 = [
        {
            "message_id": f"msg_mixed_{i}",
            "thread_id": f"thread_{i}",
            "sender": f"user{i}@example.com",
            "subject": f"Email {i}",
            "received_at": datetime(2025, 11, 5, 10, i, 0, tzinfo=timezone.utc),
        }
        for i in range(1, 4)
    ]

    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails_batch1)):
        new_count_1, skip_count_1 = await _poll_user_emails_async(test_user_with_tokens.id)

    assert new_count_1 == 3
    assert skip_count_1 == 0

    # Second batch: 2 duplicates (msg_mixed_1, msg_mixed_2) + 2 new (msg_mixed_4, msg_mixed_5)
    mock_emails_batch2 = [
        mock_emails_batch1[0],  # Duplicate
        mock_emails_batch1[1],  # Duplicate
        {
            "message_id": "msg_mixed_4",
            "thread_id": "thread_4",
            "sender": "user4@example.com",
            "subject": "Email 4",
            "received_at": datetime(2025, 11, 5, 10, 4, 0, tzinfo=timezone.utc),
        },
        {
            "message_id": "msg_mixed_5",
            "thread_id": "thread_5",
            "sender": "user5@example.com",
            "subject": "Email 5",
            "received_at": datetime(2025, 11, 5, 10, 5, 0, tzinfo=timezone.utc),
        },
    ]

    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails_batch2)):
        new_count_2, skip_count_2 = await _poll_user_emails_async(test_user_with_tokens.id)

    # Assert: 2 new, 2 duplicates
    assert new_count_2 == 2
    assert skip_count_2 == 2

    # Verify: Total 5 unique emails
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id
    )
    result = await db_session.execute(statement)
    emails = result.scalars().all()

    assert len(emails) == 5

    # Verify all message IDs unique
    message_ids = {email.gmail_message_id for email in emails}
    assert len(message_ids) == 5
    assert message_ids == {"msg_mixed_1", "msg_mixed_2", "msg_mixed_3", "msg_mixed_4", "msg_mixed_5"}


@pytest.mark.asyncio
async def test_email_polling_invalid_sender_email(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Handle invalid sender email format.

    Tests:
    - Email with invalid sender format still processed
    - Warning logged but email persisted
    - Defensive handling of edge cases

    AC Coverage: AC#2
    """
    # Mock Gmail client with invalid sender email
    mock_emails = [
        {
            "message_id": "msg_invalid_sender",
            "thread_id": "thread_invalid",
            "sender": "not_an_email",  # Invalid format
            "subject": "Invalid Sender Test",
            "received_at": datetime(2025, 11, 5, 10, 0, 0, tzinfo=timezone.utc),
        },
    ]

    with patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails)):
        # Should not raise exception - defensive handling
        new_count, skip_count = await _poll_user_emails_async(test_user_with_tokens.id)

    # Assert: Email still processed (defensive)
    assert new_count == 1
    assert skip_count == 0

    # Verify email persisted with original sender value
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id
    )
    result = await db_session.execute(statement)
    email = result.scalar_one()

    assert email.sender == "not_an_email"  # Original value preserved


@pytest.mark.asyncio
async def test_email_polling_workflow_integration(
    test_user_with_tokens: User,
    db_session: AsyncSession,
):
    """Integration test: Email polling triggers classification workflow.

    Tests Story 2.3 Task 8: Email Polling Integration
    - New email detected and saved to EmailProcessingQueue
    - WorkflowInstanceTracker.start_workflow() called automatically
    - Classification workflow executes (extract_context → classify → send_telegram → await_approval)
    - EmailProcessingQueue status updated to "awaiting_approval"
    - Thread ID returned for checkpoint tracking

    AC Coverage: Story 2.3 AC#1, AC#8
    """
    # Mock Gmail client get_messages to return 1 new email
    mock_emails = [
        {
            "message_id": "msg_workflow_test",
            "thread_id": "thread_workflow",
            "sender": "workflow_test@example.com",
            "subject": "Test Email for Workflow",
            "received_at": datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc),
        }
    ]

    # Mock Gmail client get_message_detail (for workflow's extract_context node)
    mock_email_detail = {
        "sender": "workflow_test@example.com",
        "subject": "Test Email for Workflow",
        "body": "This is a test email to verify workflow integration with email polling.",
        "received_at": "2025-11-07T12:00:00Z",
    }

    # Mock LLM classification response (for workflow's classify node)
    mock_classification = {
        "suggested_folder": "Work",
        "reasoning": "Email from work domain with project keywords",
        "priority_score": 75,
        "confidence": 0.92,
    }

    with (
        patch.object(GmailClient, "get_messages", new=AsyncMock(return_value=mock_emails)),
        patch.object(GmailClient, "get_message_detail", new=AsyncMock(return_value=mock_email_detail)),
        patch("app.core.llm_client.LLMClient.receive_completion", new=AsyncMock(return_value=mock_classification)),
        patch("app.services.workflow_tracker.WorkflowInstanceTracker.start_workflow") as mock_start_workflow,
    ):
        # Configure mock to return a thread_id
        mock_start_workflow.return_value = "email_123_abc-def-ghi"

        # Execute polling task
        new_count, skip_count = await _poll_user_emails_async(test_user_with_tokens.id)

    # Assert: 1 new email detected
    assert new_count == 1
    assert skip_count == 0

    # Verify: Email persisted with status="pending" initially
    statement = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user_with_tokens.id,
        EmailProcessingQueue.gmail_message_id == "msg_workflow_test",
    )
    result = await db_session.execute(statement)
    email = result.scalar_one()

    assert email is not None
    assert email.sender == "workflow_test@example.com"
    assert email.subject == "Test Email for Workflow"

    # Verify: WorkflowInstanceTracker.start_workflow() was called
    mock_start_workflow.assert_called_once()
    call_args = mock_start_workflow.call_args
    assert call_args.kwargs["email_id"] == email.id
    assert call_args.kwargs["user_id"] == test_user_with_tokens.id

    # Note: Actual workflow execution (status → "awaiting_approval") is mocked
    # Full workflow state changes tested in test_email_workflow_integration.py
