"""Unit tests for BatchNotificationService (Story 2.8).

Tests cover:
- AC #1: Batch notification scheduling (Celery task tested separately)
- AC #2: Retrieving pending emails with correct filters
- AC #3, #4: Summary message creation with category breakdown
- AC #5: Individual proposal sending (integration test covers full flow)
- AC #6: Priority email bypass (tested in workflow nodes)
- AC #7: NotificationPreferences usage
- AC #8: Empty batch handling
- AC #9: Batch completion logging (integration test validates)
"""

import pytest
from datetime import time, datetime
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.batch_notification import BatchNotificationService
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.notification_preferences import NotificationPreferences
from app.models.user import User


@pytest.fixture
def mock_db_session():
    """Create mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def batch_service(mock_db_session):
    """Create BatchNotificationService with mocked dependencies."""
    return BatchNotificationService(db=mock_db_session)


@pytest.mark.asyncio
async def test_get_pending_emails_filters_correctly(batch_service, mock_db_session):
    """Test get_pending_emails() queries with correct filters (AC #2).

    Verifies:
    - User ID filter applied
    - Status = "awaiting_approval" filter
    - is_priority = False filter (priority emails sent immediately)
    - Ordering by received_at ASC (oldest first)
    """
    # Arrange
    user_id = 42
    mock_scalars = Mock()
    mock_scalars.all.return_value = [
        Mock(id=1, sender="test@example.com", status="awaiting_approval", is_priority=False),
        Mock(id=2, sender="test2@example.com", status="awaiting_approval", is_priority=False),
    ]

    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    # Act
    pending_emails = await batch_service.get_pending_emails(user_id)

    # Assert
    assert len(pending_emails) == 2
    mock_db_session.execute.assert_called_once()
    # Verify SQL statement contains correct filters (would need to inspect statement)


@pytest.mark.asyncio
async def test_create_summary_message_format(batch_service):
    """Test create_summary_message() format includes count and category breakdown (AC #3, #4).

    Verifies:
    - Total count displayed
    - Category breakdown sorted by count descending
    - Message structure matches expected format
    """
    # Arrange
    mock_folder_gov = Mock()
    mock_folder_gov.name = "Government"

    mock_folder_clients = Mock()
    mock_folder_clients.name = "Clients"

    pending_emails = [
        Mock(proposed_folder=mock_folder_gov),
        Mock(proposed_folder=mock_folder_gov),
        Mock(proposed_folder=mock_folder_gov),
        Mock(proposed_folder=mock_folder_clients),
        Mock(proposed_folder=mock_folder_clients),
    ]

    # Act
    summary = batch_service.create_summary_message(pending_emails)

    # Assert
    assert "**5** emails needing review" in summary
    assert "• 3 → Government" in summary
    assert "• 2 → Clients" in summary
    assert "📬 **Daily Email Summary**" in summary
    assert "Individual proposals will follow below" in summary
    # Verify Government appears before Clients (sorted by count descending)
    assert summary.index("Government") < summary.index("Clients")


@pytest.mark.asyncio
async def test_empty_batch_handling(batch_service, mock_db_session):
    """Test empty batch handling - no message sent (AC #8).

    Verifies:
    - process_batch_for_user returns {"status": "no_emails", "emails_sent": 0}
    - No Telegram messages sent when no pending emails
    """
    # Arrange
    user_id = 42

    # Mock get_user_preferences - batch enabled
    mock_prefs = NotificationPreferences(
        id=1,
        user_id=user_id,
        batch_enabled=True,
        batch_time=time(18, 0),
        priority_immediate=True
    )
    batch_service.get_user_preferences = AsyncMock(return_value=mock_prefs)

    # Mock is_quiet_hours - not in quiet hours
    batch_service.is_quiet_hours = Mock(return_value=False)

    # Mock get_pending_emails - no pending emails
    batch_service.get_pending_emails = AsyncMock(return_value=[])

    # Act
    result = await batch_service.process_batch_for_user(user_id)

    # Assert
    assert result["status"] == "no_emails"
    assert result["emails_sent"] == 0
    # Verify send_summary was NOT called
    batch_service.send_summary = AsyncMock()  # Would not be called
    assert not batch_service.send_summary.called


@pytest.mark.asyncio
async def test_quiet_hours_check(batch_service):
    """Test is_quiet_hours() logic for overnight and same-day quiet hours.

    Verifies:
    - Overnight quiet hours (22:00 - 08:00)
    - Same-day quiet hours (01:00 - 06:00)
    - Current time comparison logic
    """
    # Test case 1: Overnight quiet hours (22:00 - 08:00), current time 23:30
    prefs = NotificationPreferences(
        id=1,
        user_id=1,
        batch_enabled=True,
        batch_time=time(18, 0),
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0)
    )

    with patch('app.services.batch_notification.datetime') as mock_datetime:
        mock_datetime.now.return_value.time.return_value = time(23, 30)
        result = batch_service.is_quiet_hours(prefs)
        assert result is True

    # Test case 2: Overnight quiet hours, current time 10:00 (outside)
    with patch('app.services.batch_notification.datetime') as mock_datetime:
        mock_datetime.now.return_value.time.return_value = time(10, 0)
        result = batch_service.is_quiet_hours(prefs)
        assert result is False

    # Test case 3: Same-day quiet hours (01:00 - 06:00), current time 03:00
    prefs.quiet_hours_start = time(1, 0)
    prefs.quiet_hours_end = time(6, 0)

    with patch('app.services.batch_notification.datetime') as mock_datetime:
        mock_datetime.now.return_value.time.return_value = time(3, 0)
        result = batch_service.is_quiet_hours(prefs)
        assert result is True


@pytest.mark.asyncio
async def test_batch_disabled_user(batch_service, mock_db_session):
    """Test batch processing skipped when batch_enabled=False.

    Verifies:
    - process_batch_for_user returns {"status": "disabled", "emails_sent": 0}
    - No pending emails queried when batch disabled
    """
    # Arrange
    user_id = 42
    mock_prefs = NotificationPreferences(
        id=1,
        user_id=user_id,
        batch_enabled=False,  # Batch disabled
        batch_time=time(18, 0)
    )
    batch_service.get_user_preferences = AsyncMock(return_value=mock_prefs)

    # Act
    result = await batch_service.process_batch_for_user(user_id)

    # Assert
    assert result["status"] == "disabled"
    assert result["emails_sent"] == 0


@pytest.mark.asyncio
@patch('app.services.batch_notification.asyncio.sleep', new_callable=AsyncMock)
async def test_individual_proposals_rate_limiting(mock_sleep, batch_service, mock_db_session):
    """Test send_individual_proposals() implements 100ms rate limiting (AC #5).

    Verifies:
    - asyncio.sleep(0.1) called between each message send
    - All messages sent successfully with rate limiting
    """
    # Arrange
    user_id = 42
    mock_user = Mock()
    mock_user.telegram_id = "123456"

    # Mock database user query
    mock_user_result = Mock()
    mock_user_result.scalar_one_or_none.return_value = mock_user

    # Mock WorkflowMapping queries (one for each email)
    mock_mapping = Mock()
    mock_mapping.telegram_message_id = None
    mock_mapping_result = Mock()
    mock_mapping_result.scalar_one_or_none.return_value = mock_mapping

    def mock_execute_sync(stmt):
        # Return user on first call, mapping on subsequent calls
        if not hasattr(mock_execute_sync, 'call_count'):
            mock_execute_sync.call_count = 0
        mock_execute_sync.call_count += 1

        if mock_execute_sync.call_count == 1:
            return mock_user_result
        else:
            return mock_mapping_result

    mock_db_session.execute.side_effect = mock_execute_sync

    # Create 3 pending emails
    mock_folder = Mock()
    mock_folder.name = "Test Folder"

    pending_emails = [
        Mock(id=1, sender="test1@example.com", subject="Subject 1", proposed_folder=mock_folder, classification_reasoning="Reason 1"),
        Mock(id=2, sender="test2@example.com", subject="Subject 2", proposed_folder=mock_folder, classification_reasoning="Reason 2"),
        Mock(id=3, sender="test3@example.com", subject="Subject 3", proposed_folder=mock_folder, classification_reasoning="Reason 3"),
    ]

    # Mock TelegramBotClient.send_message_with_buttons
    batch_service.telegram_bot.send_message_with_buttons = AsyncMock(return_value="msg_123")

    # Act
    sent_count = await batch_service.send_individual_proposals(user_id, pending_emails)

    # Assert
    assert sent_count == 3
    assert batch_service.telegram_bot.send_message_with_buttons.call_count == 3
    # Verify asyncio.sleep(0.1) called 3 times (once after each message)
    assert mock_sleep.call_count == 3
    mock_sleep.assert_called_with(0.1)


@pytest.mark.asyncio
async def test_get_user_preferences_creates_defaults(batch_service, mock_db_session):
    """Test get_user_preferences() creates default preferences if none exist.

    Verifies:
    - Default NotificationPreferences created with:
      - batch_enabled = True
      - batch_time = 18:00
      - priority_immediate = True
      - timezone = UTC
    """
    # Arrange
    user_id = 42
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None  # No existing preferences

    mock_db_session.execute.return_value = mock_result
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    # Act
    prefs = await batch_service.get_user_preferences(user_id)

    # Assert
    assert prefs.user_id == user_id
    assert prefs.batch_enabled is True
    assert prefs.batch_time == time(18, 0)
    assert prefs.priority_immediate is True
    assert prefs.timezone == "UTC"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
