"""
Integration test for draft notification deduplication on workflow resume.

This test verifies the fix for the bug where send_response_draft_notification
would send duplicate Telegram messages when workflow resumed after interrupt().

Bug context:
- When using Command(resume=...), LangGraph re-executes the entire node
- Without state checks, notification was sent twice (once on first run, once on resume)
- This caused draft_telegram_message_id to be overwritten, breaking message deletion

Test validates:
1. Draft notification sent ONCE on first pause
2. No duplicate notification on resume with Command(resume=...)
3. draft_telegram_message_id preserved across resume
4. Both messages (sorting + draft) deleted in send_confirmation

Created: 2025-12-06
Issue: Draft notification duplication on workflow resume
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.email_workflow import create_email_workflow
from app.workflows.states import EmailWorkflowState
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.workflow_mapping import WorkflowMapping
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from app.core.encryption import encrypt_token

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../mocks'))
from gemini_mock import MockGeminiClient
from gmail_mock import MockGmailClient
from telegram_mock import MockTelegramBot


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user with tokens."""
    access_token = encrypt_token("test_access_token")
    refresh_token = encrypt_token("test_refresh_token")

    user = User(
        email="draft_test@gmail.com",
        is_active=True,
        telegram_id="987654321",
        telegram_username="drafttest",
        telegram_linked_at=datetime.now(UTC),
        gmail_oauth_token=access_token,
        gmail_refresh_token=refresh_token,
        gmail_connected_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_folder(db_session: AsyncSession, test_user: User) -> FolderCategory:
    """Create test folder."""
    folder = FolderCategory(
        user_id=test_user.id,
        name="Important",
        gmail_label_id="Label_Important_123",
        keywords=["urgent"],
        priority_domains=[],
        is_system_folder=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)
    return folder


@pytest_asyncio.fixture
async def test_email(db_session: AsyncSession, test_user: User) -> EmailProcessingQueue:
    """Create test email for workflow."""
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id=f"test_msg_{uuid4().hex[:16]}",
        gmail_thread_id=f"test_thread_{uuid4().hex[:16]}",
        sender="sender@example.com",
        subject="Test Email for Draft - This is a test email that needs response",
        received_at=datetime.now(UTC),
        status="pending",
        classification=None,
        priority_score=50,
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    return email


@pytest.mark.asyncio
async def test_draft_notification_sent_only_once_on_resume(
    db_session: AsyncSession,
    workflow_db_session_factory,
    test_user: User,
    test_folder: FolderCategory,
    test_email: EmailProcessingQueue,
):
    """
    Test that draft notification is sent only ONCE even when workflow resumes.

    Workflow steps:
    1. Start workflow with needs_response classification
    2. User approves sorting → workflow sends draft notification (FIRST pause)
    3. Verify: draft notification sent ONCE, draft_telegram_message_id in state
    4. User clicks [Send] → workflow resumes with Command(resume="send_response")
    5. Verify: NO duplicate draft notification sent
    6. Verify: draft_telegram_message_id PRESERVED in state
    7. Verify: Both messages deleted in send_confirmation
    """

    # Mock services
    mock_telegram = MockTelegramBot()
    mock_gmail = MockGmailClient()
    mock_gemini = MockGeminiClient()

    # Track Telegram message sends
    telegram_messages_sent = []
    original_send = mock_telegram.send_message_with_buttons

    async def track_send_message(*args, **kwargs):
        result = await original_send(*args, **kwargs)
        telegram_messages_sent.append({
            "telegram_id": kwargs.get("telegram_id"),
            "text": kwargs.get("text"),
            "message_id": result,
        })
        return result

    mock_telegram.send_message_with_buttons = track_send_message

    # Mock classification to return needs_response
    mock_gemini.classification_response = {
        "suggested_folder": "Important",
        "reasoning": "Test needs response",
        "priority_score": 80,
        "confidence": 0.9,
        "needs_response": True,
        "response_draft": "Thank you for your email. I will review it shortly.",
    }

    # Mock context retrieval
    mock_context_service = AsyncMock()
    mock_context_service.retrieve_context = AsyncMock(return_value={
        "thread_history": [],
        "semantic_results": [],
        "metadata": {
            "thread_length": 0,
            "semantic_count": 0,
            "total_tokens_used": 0
        }
    })

    # Mock embedding service
    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    # Mock vector DB client
    mock_vector_db_client = AsyncMock()

    # Create workflow with PostgresSaver and pass mock services directly
    checkpointer = PostgresSaver(workflow_db_session_factory)
    workflow = create_email_workflow(
        checkpointer=checkpointer,
        db_session_factory=workflow_db_session_factory,
        gmail_client=mock_gmail,
        llm_client=mock_gemini,
        telegram_client=mock_telegram,
        context_service=mock_context_service,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
    )

    # Initialize workflow state
    thread_id = f"test_draft_{uuid4()}"
    initial_state = EmailWorkflowState(
        email_id=str(test_email.id),
        user_id=str(test_user.id),
        sender=test_email.sender,
        subject=test_email.subject,
        body=test_email.subject,  # EmailProcessingQueue doesn't have body field, use subject
        thread_id=thread_id,
        gmail_message_id=test_email.gmail_message_id,
        gmail_thread_id=test_email.gmail_thread_id,
    )

    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",
        }
    }

    # Create workflow mapping
    workflow_mapping = WorkflowMapping(
        email_id=test_email.id,
        user_id=test_user.id,
        thread_id=thread_id,
        workflow_state="pending",
        telegram_message_id=None,
    )
    db_session.add(workflow_mapping)
    await db_session.commit()

    # Step 1: Start workflow and approve sorting
    # This will execute until first interrupt (await_approval)
    result = await workflow.ainvoke(initial_state, config=config)

    # Verify workflow paused at await_approval
    state_after_first_pause = await workflow.aget_state(config)
    assert state_after_first_pause.next == ("await_approval",), \
        f"Expected pause at await_approval, got {state_after_first_pause.next}"

    # Step 2: User approves sorting → workflow continues to draft notification
    result = await workflow.ainvoke(Command(resume="approve"), config=config)

    # Verify workflow paused at send_response_draft_notification (second interrupt)
    state_after_second_pause = await workflow.aget_state(config)

    # Count draft notifications sent so far
    draft_messages_before_resume = [
        msg for msg in telegram_messages_sent
        if "черновик" in msg["text"].lower() or "draft" in msg["text"].lower()
    ]

    print(f"\n✓ Draft notifications sent before resume: {len(draft_messages_before_resume)}")
    assert len(draft_messages_before_resume) == 1, \
        f"Expected 1 draft notification before resume, got {len(draft_messages_before_resume)}"

    # Extract draft_telegram_message_id from state
    draft_message_id_before = state_after_second_pause.values.get("draft_telegram_message_id")
    print(f"✓ draft_telegram_message_id before resume: {draft_message_id_before}")
    assert draft_message_id_before is not None, \
        "draft_telegram_message_id should be set after first draft notification"

    # Step 3: User clicks [Send] → workflow resumes with Command(resume="send_response")
    result = await workflow.ainvoke(Command(resume="send_response"), config=config)

    # Verify NO duplicate draft notification sent
    draft_messages_after_resume = [
        msg for msg in telegram_messages_sent
        if "черновик" in msg["text"].lower() or "draft" in msg["text"].lower()
    ]

    print(f"✓ Draft notifications sent after resume: {len(draft_messages_after_resume)}")
    assert len(draft_messages_after_resume) == 1, \
        f"Expected STILL 1 draft notification after resume (no duplicate), got {len(draft_messages_after_resume)}"

    # Verify draft_telegram_message_id PRESERVED
    state_after_resume = await workflow.aget_state(config)
    draft_message_id_after = state_after_resume.values.get("draft_telegram_message_id")

    print(f"✓ draft_telegram_message_id after resume: {draft_message_id_after}")
    assert draft_message_id_after == draft_message_id_before, \
        f"draft_telegram_message_id should be preserved! Before: {draft_message_id_before}, After: {draft_message_id_after}"

    # Step 4: Verify both messages deleted
    print(f"✓ Messages deleted: {mock_telegram.deleted_messages}")

    # Should delete:
    # 1. Sorting proposal message
    # 2. Draft notification message
    assert len(mock_telegram.deleted_messages) >= 2, \
        f"Expected at least 2 messages deleted (sorting + draft), got {len(mock_telegram.deleted_messages)}"

    # Verify draft notification message was deleted
    assert draft_message_id_before in mock_telegram.deleted_messages, \
        f"Draft notification (message_id: {draft_message_id_before}) should be deleted!"

    print("\n✅ TEST PASSED: Draft notification sent only once, no duplicates on resume!")
    print(f"   - Draft notifications sent: {len(draft_messages_after_resume)}")
    print(f"   - draft_telegram_message_id preserved: {draft_message_id_before}")
    print(f"   - Messages deleted: {len(mock_telegram.deleted_messages)}")


@pytest.mark.asyncio
async def test_draft_notification_has_sent_flag_in_state(
    db_session: AsyncSession,
    workflow_db_session_factory,
    test_user: User,
    test_folder: FolderCategory,
    test_email: EmailProcessingQueue,
):
    """
    Test that draft_notification_sent flag is properly set in state.

    This flag is critical for preventing duplicate notifications on resume.
    """

    mock_telegram = MockTelegramBot()
    mock_gmail = MockGmailClient()
    mock_gemini = MockGeminiClient()

    mock_gemini.classification_response = {
        "suggested_folder": "Important",
        "reasoning": "Test",
        "priority_score": 80,
        "confidence": 0.9,
        "needs_response": True,
        "response_draft": "Test draft",
    }

    mock_context_service = AsyncMock()
    mock_context_service.retrieve_context = AsyncMock(return_value={
        "thread_history": [],
        "semantic_results": [],
        "metadata": {"thread_length": 0, "semantic_count": 0, "total_tokens_used": 0}
    })

    # Mock embedding service
    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    # Mock vector DB client
    mock_vector_db_client = AsyncMock()

    checkpointer = PostgresSaver(workflow_db_session_factory)
    workflow = create_email_workflow(
        checkpointer=checkpointer,
        db_session_factory=workflow_db_session_factory,
        gmail_client=mock_gmail,
        llm_client=mock_gemini,
        telegram_client=mock_telegram,
        context_service=mock_context_service,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
    )

    thread_id = f"test_flag_{uuid4()}"
    initial_state = EmailWorkflowState(
        email_id=str(test_email.id),
        user_id=str(test_user.id),
        sender=test_email.sender,
        subject=test_email.subject,
        body=test_email.subject,  # EmailProcessingQueue doesn't have body field, use subject
        thread_id=thread_id,
        gmail_message_id=test_email.gmail_message_id,
        gmail_thread_id=test_email.gmail_thread_id,
    )

    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}

    workflow_mapping = WorkflowMapping(
        email_id=test_email.id,
        user_id=test_user.id,
        thread_id=thread_id,
        workflow_state="pending",
    )
    db_session.add(workflow_mapping)
    await db_session.commit()

    # Execute to await_approval
    await workflow.ainvoke(initial_state, config=config)

    # Approve sorting → execute to draft notification
    await workflow.ainvoke(Command(resume="approve"), config=config)

    # Check state has draft_notification_sent flag
    state = await workflow.aget_state(config)

    assert state.values.get("draft_notification_sent") == True, \
        "draft_notification_sent flag should be True after sending draft notification"

    print("✅ TEST PASSED: draft_notification_sent flag correctly set in state")
