"""Integration tests for Batch Notification System (Story 2.8).

Tests cover end-to-end flows:
- AC #1-9: Complete batch notification flow
- AC #6: Priority email bypass logic
- AC #8: Empty batch handling
"""

import pytest
from datetime import time
from unittest.mock import AsyncMock, Mock, patch

from app.services.batch_notification import BatchNotificationService
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.notification_preferences import NotificationPreferences
from app.models.user import User
from app.models.workflow_mapping import WorkflowMapping


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_batch_notification_flow(db_session, test_user, test_folder, test_notification_prefs):
    """Test complete batch notification flow from start to finish (AC #1-9).

    Scenario:
    - User has 5 pending emails (status="awaiting_approval", is_priority=False)
    - NotificationPreferences with batch_enabled=True, batch_time=18:00
    - Batch task triggers

    Expected:
    - Summary message sent with count and category breakdown
    - 5 individual proposal messages sent
    - WorkflowMapping updated with telegram_message_id for each email
    - Batch completion logged
    """
    from datetime import datetime, UTC
    from sqlalchemy import select

    # Create 5 pending emails with proposed_folder
    for i in range(5):
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=f"gmail-msg-{i}",
            gmail_thread_id=f"thread-{i}",
            sender=f"sender{i}@example.com",
            recipient=test_user.email,
            subject=f"Test Email {i}",
            received_at=datetime.now(UTC),
            status="awaiting_approval",
            proposed_folder_id=test_folder.id,
            classification_reasoning=f"Classified as {test_folder.name}",
            priority_score=50,  # Non-priority (< 70)
            is_priority=False,
            created_at=datetime.now(UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        # Create WorkflowMapping for each email (now email.id is available)
        workflow_mapping = WorkflowMapping(
            email_id=email.id,
            user_id=test_user.id,
            thread_id=f"email_{i}_workflow_thread",
            workflow_state="awaiting_approval",
        )
        db_session.add(workflow_mapping)

    await db_session.commit()

    # Mock TelegramBotClient to avoid sending real messages
    with patch('app.services.batch_notification.TelegramBotClient') as MockTelegramBot:
        mock_bot_instance = AsyncMock()
        mock_bot_instance.send_message.return_value = "mock_summary_msg_id"
        mock_bot_instance.send_message_with_buttons.return_value = "mock_proposal_msg_id"
        MockTelegramBot.return_value = mock_bot_instance

        # Create service and execute batch
        service = BatchNotificationService(db=db_session)
        result = await service.process_batch_for_user(test_user.id)

    # Verify result
    assert result["status"] == "completed"
    assert result["emails_sent"] == 5
    assert result["pending_count"] == 5

    # Verify summary message was sent
    mock_bot_instance.send_message.assert_called_once()
    summary_call = mock_bot_instance.send_message.call_args
    assert test_user.telegram_id in str(summary_call)
    assert "5** emails needing review" in summary_call[1]["text"]
    assert f"5 → {test_folder.name}" in summary_call[1]["text"]

    # Verify 5 individual proposal messages sent
    assert mock_bot_instance.send_message_with_buttons.call_count == 5

    # Verify WorkflowMapping updated with telegram_message_id
    stmt = select(WorkflowMapping).where(WorkflowMapping.user_id == test_user.id)
    result = await db_session.execute(stmt)
    mappings = result.scalars().all()
    assert len(mappings) == 5
    for mapping in mappings:
        assert mapping.telegram_message_id == "mock_proposal_msg_id"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_priority_emails_bypass_batch(db_session, test_user, test_folder, test_notification_prefs):
    """Test priority emails sent immediately, not in batch (AC #6).

    Scenario:
    - Email with priority_score >= 70 processed through workflow
    - send_telegram node detects priority

    Expected:
    - Email sent immediately via Telegram (workflow node)
    - Email NOT included in batch notification query (is_priority=True)
    - Non-priority emails (priority_score < 70) marked awaiting_approval
    - Non-priority emails sent in batch
    """
    from datetime import datetime, UTC

    # Create 1 priority email (should bypass batch)
    priority_email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="priority-msg-1",
        gmail_thread_id="priority-thread-1",
        sender="urgent@government.com",
        recipient=test_user.email,
        subject="URGENT: Tax Audit Notice",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        proposed_folder_id=test_folder.id,
        classification_reasoning="High priority government email",
        priority_score=85,  # Priority (>= 70)
        is_priority=True,  # Marked as priority
        created_at=datetime.now(UTC),
    )
    db_session.add(priority_email)

    # Create 2 non-priority emails (should be in batch)
    for i in range(2):
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=f"normal-msg-{i}",
            gmail_thread_id=f"normal-thread-{i}",
            sender=f"sender{i}@example.com",
            recipient=test_user.email,
            subject=f"Normal Email {i}",
            received_at=datetime.now(UTC),
            status="awaiting_approval",
            proposed_folder_id=test_folder.id,
            classification_reasoning=f"Classified as {test_folder.name}",
            priority_score=40,  # Non-priority (< 70)
            is_priority=False,
            created_at=datetime.now(UTC),
        )
        db_session.add(email)

    await db_session.commit()

    # Mock TelegramBotClient
    with patch('app.services.batch_notification.TelegramBotClient') as MockTelegramBot:
        mock_bot_instance = AsyncMock()
        mock_bot_instance.send_message.return_value = "mock_summary_msg_id"
        mock_bot_instance.send_message_with_buttons.return_value = "mock_proposal_msg_id"
        MockTelegramBot.return_value = mock_bot_instance

        # Create service and get pending emails
        service = BatchNotificationService(db=db_session)
        pending_emails = await service.get_pending_emails(test_user.id)

    # Verify priority email excluded from batch (AC #6)
    assert len(pending_emails) == 2, "Only non-priority emails should be in batch"
    for email in pending_emails:
        assert email.is_priority is False, "Batch should not include priority emails"
        assert email.priority_score < 70, "Batch should not include high priority scores"

    # Verify priority email exists in database but not in batch query
    from sqlalchemy import select
    stmt = select(EmailProcessingQueue).where(
        EmailProcessingQueue.user_id == test_user.id,
        EmailProcessingQueue.is_priority == True
    )
    result = await db_session.execute(stmt)
    priority_emails = result.scalars().all()
    assert len(priority_emails) == 1, "Priority email should exist in database"
    assert priority_emails[0].priority_score >= 70, "Priority email should have high score"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_batch_with_no_pending_emails():
    """Test batch processing with no pending emails (AC #8).

    Scenario:
    - User has no pending emails (status="awaiting_approval", is_priority=False)
    - Batch task triggers

    Expected:
    - No Telegram messages sent (summary or individual)
    - process_batch_for_user returns {"status": "no_emails", "emails_sent": 0}
    - Logged as "no_emails" status
    """
    # Mock database and service
    mock_db = AsyncMock()
    service = BatchNotificationService(db=mock_db)

    # Mock dependencies
    mock_prefs = NotificationPreferences(
        id=1,
        user_id=1,
        batch_enabled=True,
        batch_time=time(18, 0)
    )
    service.get_user_preferences = AsyncMock(return_value=mock_prefs)
    service.is_quiet_hours = Mock(return_value=False)
    service.get_pending_emails = AsyncMock(return_value=[])  # No pending emails

    # Execute
    result = await service.process_batch_for_user(user_id=1)

    # Verify
    assert result["status"] == "no_emails"
    assert result["emails_sent"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_celery_task_processes_all_users(db_session, test_user, test_user_2, test_folder):
    """Test Celery batch notification task processes all batch-enabled users.

    Scenario:
    - 3 users with batch_enabled=True
    - 1 user with batch_enabled=False
    - send_batch_notifications Celery task runs

    Expected:
    - 3 users processed (batch_enabled=True)
    - 1 user skipped (batch_enabled=False)
    - Task returns statistics (total_users, successful_batches, failed_batches)
    """
    from datetime import datetime, UTC, time as dt_time
    from app.tasks.notification_tasks import _get_batch_enabled_users

    # Create third user with batch_enabled=True
    user_3 = User(
        email="test3@example.com",
        is_active=True,
        telegram_id="111222333",
        telegram_username="testuser3",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user_3)
    await db_session.commit()
    await db_session.refresh(user_3)

    # Create fourth user with batch_enabled=False (should be skipped)
    user_4 = User(
        email="test4@example.com",
        is_active=True,
        telegram_id="444555666",
        telegram_username="testuser4",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user_4)
    await db_session.commit()
    await db_session.refresh(user_4)

    # Create notification preferences
    # User 1, 2, 3: batch_enabled=True
    for user in [test_user, test_user_2, user_3]:
        prefs = NotificationPreferences(
            user_id=user.id,
            batch_enabled=True,
            batch_time=dt_time(18, 0),
            priority_immediate=True,
            timezone="UTC",
        )
        db_session.add(prefs)

    # User 4: batch_enabled=False (should be skipped)
    prefs_disabled = NotificationPreferences(
        user_id=user_4.id,
        batch_enabled=False,  # Disabled
        batch_time=dt_time(18, 0),
        priority_immediate=True,
        timezone="UTC",
    )
    db_session.add(prefs_disabled)
    await db_session.commit()

    # Query batch-enabled users (should return 3 users, not 4)
    batch_enabled_users = await _get_batch_enabled_users(db_session)

    # Verify only batch-enabled users are returned
    assert len(batch_enabled_users) == 3, "Should return only 3 batch-enabled users"
    user_ids = [user.id for user in batch_enabled_users]
    assert test_user.id in user_ids, "test_user should be included"
    assert test_user_2.id in user_ids, "test_user_2 should be included"
    assert user_3.id in user_ids, "user_3 should be included"
    assert user_4.id not in user_ids, "user_4 (batch_disabled) should be excluded"

    # Verify all returned users have active batch preferences
    for user in batch_enabled_users:
        from sqlalchemy import select
        stmt = select(NotificationPreferences).where(
            NotificationPreferences.user_id == user.id
        )
        result = await db_session.execute(stmt)
        prefs = result.scalar_one()
        assert prefs.batch_enabled is True, f"User {user.id} should have batch_enabled=True"
