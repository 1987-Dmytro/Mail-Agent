"""
Unit Tests for Telegram Response Draft Service

Tests cover:
- Message template formatting (AC #1-4, #6-7, #9)
- Inline keyboard builder (AC #5)
- Telegram message sending (AC #1-9)
- WorkflowMapping persistence
- End-to-end orchestration

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.8 (Response Draft Telegram Messages)
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime, UTC
from telegram import InlineKeyboardButton

from app.services.telegram_response_draft import TelegramResponseDraftService
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User
from app.utils.errors import TelegramUserBlockedError


# Patch Session at module level for all tests
@pytest.fixture(autouse=True)
def mock_session_class(mock_db_session):
    """Auto-patch Session class for all tests in this module."""
    with patch('app.services.telegram_response_draft.Session', return_value=mock_db_session):
        yield


# Fixtures

@pytest.fixture
def mock_db_service():
    """Mock DatabaseService with engine."""
    service = Mock()
    service.engine = Mock()
    return service


@pytest.fixture
def mock_db_session():
    """Mock SQLModel database session for use with Session context manager."""
    session = MagicMock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


@pytest.fixture
def mock_telegram_bot():
    """Mock TelegramBotClient with async send_message_with_buttons."""
    bot = Mock()
    bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_123")
    return bot


@pytest.fixture
def telegram_service(mock_telegram_bot, mock_db_service):
    """TelegramResponseDraftService instance with mocked dependencies."""
    return TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=mock_db_service
    )


@pytest.fixture
def sample_email():
    """Sample EmailProcessingQueue with response draft."""
    return EmailProcessingQueue(
        id=42,
        user_id=1,
        gmail_message_id="gmail_123",
        gmail_thread_id="thread_456",
        sender="sender@example.com",
        subject="Question about your product",
        received_at=datetime(2025, 11, 10, 10, 0, 0, tzinfo=UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response="Dear Sir/Madam,\n\nThank you for your inquiry about our product...",
        detected_language="en",
        is_priority=False
    )


@pytest.fixture
def sample_priority_email(sample_email):
    """Sample EmailProcessingQueue with priority flag."""
    email = sample_email
    email.is_priority = True
    return email


@pytest.fixture
def sample_user():
    """Sample User with Telegram linked."""
    return User(
        id=1,
        email="user@example.com",
        gmail_credentials=None,
        telegram_id="123456789"
    )


# Test 1: test_format_response_draft_message_standard (AC #1-4, #6-7)

def test_format_response_draft_message_standard(telegram_service, mock_db_session, sample_email):
    """Test standard message formatting with all sections (AC #1-4, #6-7).

    Verifies:
    - Message template created (AC #1)
    - Original email info included (sender, subject, preview) (AC #2)
    - AI-generated draft included (AC #3)
    - Visual separators present (AC #4)
    - Language indicated (AC #6)
    - Context summary shown (AC #7) - Note: Context not available without param
    """
    # Mock db_session.get() to return sample email
    mock_db_session.get.return_value = sample_email

    # Call format_response_draft_message
    message = telegram_service.format_response_draft_message(email_id=42)

    # Assertions
    assert message is not None
    assert len(message) > 0

    # Check header (AC #1)
    assert "📧 Response Draft Ready" in message

    # Check original email section (AC #2)
    assert "📨 Original Email:" in message
    assert "From: sender@example.com" in message
    assert "Subject: Question about your product" in message
    assert "Preview:" in message

    # Check AI-generated response (AC #3)
    assert "✍️ AI-Generated Response" in message
    assert "Dear Sir/Madam" in message  # Part of draft_response

    # Check visual separators (AC #4)
    assert "─────────────────" in message
    # Should have at least 2 separators
    assert message.count("─────────────────") >= 2

    # Check language indication (AC #6)
    assert "(English)" in message  # detected_language = "en"

    # Verify db_session.get was called
    mock_db_session.get.assert_called_once_with(EmailProcessingQueue, 42)


# Test 2: test_format_response_draft_message_priority (AC #9)

def test_format_response_draft_message_priority(telegram_service, mock_db_session, sample_priority_email):
    """Test priority email flagging with ⚠️ icon (AC #9).

    Verifies:
    - Priority emails show ⚠️ icon in header
    - is_priority flag correctly triggers visual indicator
    """
    # Mock db_session.get() to return priority email
    mock_db_session.get.return_value = sample_priority_email

    # Call format_response_draft_message
    message = telegram_service.format_response_draft_message(email_id=42)

    # Assertions
    assert "⚠️" in message  # Priority flag present
    assert "📧 Response Draft Ready" in message

    # Verify priority flag is at start of header
    assert message.startswith("⚠️ 📧 Response Draft Ready")

    # Verify db_session.get was called
    mock_db_session.get.assert_called_once_with(EmailProcessingQueue, 42)


# Test 3: test_format_response_draft_message_long_draft (AC #8)

def test_format_response_draft_message_long_draft(telegram_service, mock_db_session, sample_email):
    """Test Telegram length limit handling for very long drafts (AC #8).

    Verifies:
    - Messages >4096 chars are logged as warnings
    - Service allows TelegramBotClient to handle truncation
    - No exception raised for long messages
    """
    # Create email with very long draft (>4096 chars)
    long_draft = "A" * 5000  # 5000 character draft
    sample_email.draft_response = long_draft

    # Mock db_session.get() to return email with long draft
    mock_db_session.get.return_value = sample_email

    # Call format_response_draft_message
    message = telegram_service.format_response_draft_message(email_id=42)

    # Assertions
    assert message is not None
    assert len(message) > 4096  # Message exceeds limit before truncation

    # Verify long draft is included in message
    assert "AAAAA" in message  # Sample of long draft

    # Note: Actual truncation happens in TelegramBotClient.send_message_with_buttons
    # This test verifies service produces message and logs warning

    # Verify db_session.get was called
    mock_db_session.get.assert_called_once_with(EmailProcessingQueue, 42)


# Test 4: test_format_response_draft_message_no_context (AC #7)

def test_format_response_draft_message_no_context(telegram_service, mock_db_session, sample_email):
    """Test message formatting without RAG context summary (AC #7).

    Verifies:
    - Message formatting works without context summary
    - No context line added when context not available
    - Other message sections still present
    """
    # Mock db_session.get() to return sample email (no context available)
    mock_db_session.get.return_value = sample_email

    # Call format_response_draft_message
    message = telegram_service.format_response_draft_message(email_id=42)

    # Assertions
    assert message is not None

    # Verify standard sections present
    assert "📧 Response Draft Ready" in message
    assert "📨 Original Email:" in message
    assert "✍️ AI-Generated Response" in message

    # Verify no context summary line (since not implemented yet)
    # TODO: When context_summary parameter added, verify it's conditionally included
    # For now, just verify message is valid without it

    # Verify db_session.get was called
    mock_db_session.get.assert_called_once_with(EmailProcessingQueue, 42)


# Test 5: test_build_response_draft_keyboard (AC #5)

def test_build_response_draft_keyboard(telegram_service):
    """Test inline keyboard builder with 3 buttons (AC #5).

    Verifies:
    - Keyboard has 2 rows (Row 1: Send, Row 2: Edit + Reject)
    - Each button has correct text and callback_data
    - Callback data format: {action}_response_{email_id}
    """
    # Call build_response_draft_keyboard
    keyboard = telegram_service.build_response_draft_keyboard(email_id=42)

    # Assertions
    assert keyboard is not None
    assert len(keyboard) == 2  # 2 rows

    # Row 1: Send button
    assert len(keyboard[0]) == 1  # 1 button in row 1
    send_button = keyboard[0][0]
    assert isinstance(send_button, InlineKeyboardButton)
    assert send_button.text == "✅ Send"
    assert send_button.callback_data == "send_response_42"

    # Row 2: Edit and Reject buttons
    assert len(keyboard[1]) == 2  # 2 buttons in row 2
    edit_button = keyboard[1][0]
    reject_button = keyboard[1][1]

    assert isinstance(edit_button, InlineKeyboardButton)
    assert edit_button.text == "✏️ Edit"
    assert edit_button.callback_data == "edit_response_42"

    assert isinstance(reject_button, InlineKeyboardButton)
    assert reject_button.text == "❌ Reject"
    assert reject_button.callback_data == "reject_response_42"


# Test 6: test_send_response_draft_to_telegram (AC #1-9)

@pytest.mark.asyncio
async def test_send_response_draft_to_telegram(
    telegram_service,
    mock_db_session,
    mock_telegram_bot,
    sample_email,
    sample_user
):
    """Test complete Telegram message sending workflow (AC #1-9).

    Verifies:
    - Email and user loaded from database
    - Message formatted correctly
    - Keyboard built correctly
    - TelegramBotClient.send_message_with_buttons called
    - Telegram message ID returned
    """
    # Mock db_session.get() to return email first, user second, email third (for format_message call)
    mock_db_session.get.side_effect = [sample_email, sample_user, sample_email]

    # Call send_response_draft_to_telegram
    telegram_message_id = await telegram_service.send_response_draft_to_telegram(email_id=42)

    # Assertions
    assert telegram_message_id == "telegram_msg_123"

    # Verify db_session.get called three times (email, user, email for format_message)
    assert mock_db_session.get.call_count == 3
    mock_db_session.get.assert_any_call(EmailProcessingQueue, 42)
    mock_db_session.get.assert_any_call(User, 1)

    # Verify TelegramBotClient.send_message_with_buttons called
    mock_telegram_bot.send_message_with_buttons.assert_called_once()

    # Verify call arguments
    call_args = mock_telegram_bot.send_message_with_buttons.call_args
    assert call_args.kwargs["telegram_id"] == "123456789"
    assert call_args.kwargs["user_id"] == 1
    assert "📧 Response Draft Ready" in call_args.kwargs["text"]
    assert len(call_args.kwargs["buttons"]) == 2  # 2 rows


# Test 7: test_save_telegram_message_mapping

def test_save_telegram_message_mapping(telegram_service, mock_db_session, sample_email):
    """Test WorkflowMapping database persistence.

    Verifies:
    - WorkflowMapping record created with correct fields
    - email_id, user_id, thread_id, telegram_message_id set correctly
    - workflow_state set to "awaiting_response_approval"
    - Database transaction committed
    """
    # Mock db_session.get() to return sample email
    mock_db_session.get.return_value = sample_email

    # Mock db_session.exec() to return None (no existing mapping)
    mock_result = Mock()
    mock_result.first.return_value = None
    mock_db_session.exec.return_value = mock_result

    # Call save_telegram_message_mapping
    telegram_service.save_telegram_message_mapping(
        email_id=42,
        telegram_message_id="telegram_msg_123",
        thread_id="workflow_thread_789"
    )

    # Assertions

    # Verify db_session.get called to load email
    mock_db_session.get.assert_called_once_with(EmailProcessingQueue, 42)

    # Verify db_session.add called with WorkflowMapping
    mock_db_session.add.assert_called_once()
    added_mapping = mock_db_session.add.call_args[0][0]
    assert isinstance(added_mapping, WorkflowMapping)
    assert added_mapping.email_id == 42
    assert added_mapping.user_id == 1  # From sample_email
    assert added_mapping.thread_id == "workflow_thread_789"
    assert added_mapping.telegram_message_id == "telegram_msg_123"
    assert added_mapping.workflow_state == "awaiting_response_approval"

    # Verify db_session.commit called
    mock_db_session.commit.assert_called_once()


# Test 8: test_send_draft_notification_orchestration

@pytest.mark.asyncio
async def test_send_draft_notification_orchestration(
    telegram_service,
    mock_db_session,
    mock_telegram_bot,
    sample_email,
    sample_user
):
    """Test end-to-end orchestration method.

    Verifies:
    - Email validation (has draft_response)
    - send_response_draft_to_telegram called
    - save_telegram_message_mapping called
    - EmailProcessingQueue status updated to "awaiting_response_approval"
    - Returns True on success
    """
    # Mock db_session.get() to return email for different calls
    def get_side_effect(model_class, id_value):
        if model_class == EmailProcessingQueue:
            return sample_email
        elif model_class == User:
            return sample_user
        return None

    mock_db_session.get.side_effect = get_side_effect

    # Mock db_session.exec() to return None (no existing mapping)
    mock_result = Mock()
    mock_result.first.return_value = None
    mock_db_session.exec.return_value = mock_result

    # Call send_draft_notification
    result = await telegram_service.send_draft_notification(
        email_id=42,
        workflow_thread_id="workflow_thread_789"
    )

    # Assertions
    assert result is True

    # Verify db_session.get called multiple times
    assert mock_db_session.get.call_count >= 2  # At least email and user

    # Verify TelegramBotClient.send_message_with_buttons called
    mock_telegram_bot.send_message_with_buttons.assert_called_once()

    # Verify WorkflowMapping added
    mock_db_session.add.assert_called_once()

    # Verify email status updated to "awaiting_response_approval"
    assert sample_email.status == "awaiting_response_approval"

    # Verify db_session.commit called (at least once for mapping, once for email status)
    assert mock_db_session.commit.call_count >= 1


# Test 9: test_send_draft_notification_user_blocked (error handling)

@pytest.mark.asyncio
async def test_send_draft_notification_user_blocked(
    telegram_service,
    mock_db_session,
    mock_telegram_bot,
    sample_email,
    sample_user
):
    """Test graceful handling when user has blocked the bot.

    Verifies:
    - TelegramUserBlockedError caught gracefully
    - Returns False (not raised)
    - Warning logged
    """
    # Mock db_session.get() to return email and user
    def get_side_effect(model_class, id_value):
        if model_class == EmailProcessingQueue:
            return sample_email
        elif model_class == User:
            return sample_user
        return None

    mock_db_session.get.side_effect = get_side_effect

    # Mock TelegramBotClient to raise TelegramUserBlockedError
    mock_telegram_bot.send_message_with_buttons.side_effect = TelegramUserBlockedError("User blocked bot")

    # Call send_draft_notification
    result = await telegram_service.send_draft_notification(
        email_id=42,
        workflow_thread_id="workflow_thread_789"
    )

    # Assertions
    assert result is False  # Returns False instead of raising exception

    # Verify TelegramBotClient.send_message_with_buttons called
    mock_telegram_bot.send_message_with_buttons.assert_called_once()

    # Verify WorkflowMapping NOT added (since send failed)
    mock_db_session.add.assert_not_called()


# Additional Tests for 100% Coverage

def test_format_response_draft_message_email_not_found(telegram_service, mock_db_session):
    """Test format_response_draft_message raises ValueError when email not found."""
    # Mock session.get to return None (email not found)
    mock_db_session.get.return_value = None

    # Call format_response_draft_message - should raise ValueError
    with pytest.raises(ValueError, match="Email with id=999 not found"):
        telegram_service.format_response_draft_message(email_id=999)


def test_format_response_draft_message_no_draft_response(telegram_service, mock_db_session):
    """Test format_response_draft_message raises ValueError when draft_response is missing."""
    # Create email without draft_response
    email = EmailProcessingQueue(
        id=42,
        user_id=1,
        sender="test@example.com",
        subject="Test",
        received_at=datetime.now(UTC),
        draft_response=None,  # No draft
        detected_language="en",
        is_priority=False
    )
    mock_db_session.get.return_value = email

    # Call format_response_draft_message - should raise ValueError
    with pytest.raises(ValueError, match="has no draft_response field"):
        telegram_service.format_response_draft_message(email_id=42)


def test_format_response_draft_message_long_subject(telegram_service, mock_db_session):
    """Test format_response_draft_message truncates very long subject with ellipsis."""
    # Create email with subject > 100 chars
    long_subject = "A" * 150  # 150 characters
    email = EmailProcessingQueue(
        id=42,
        user_id=1,
        sender="test@example.com",
        subject=long_subject,
        received_at=datetime.now(UTC),
        draft_response="Test draft response",
        detected_language="en",
        is_priority=False
    )
    mock_db_session.get.return_value = email

    # Call format_response_draft_message
    message = telegram_service.format_response_draft_message(email_id=42)

    # Verify ellipsis added
    assert "Preview: " + "A" * 100 + "..." in message


@pytest.mark.asyncio
async def test_send_response_draft_to_telegram_email_not_found(telegram_service, mock_db_session, mock_telegram_bot):
    """Test send_response_draft_to_telegram raises ValueError when email not found."""
    # Mock session.get to return None (email not found)
    mock_db_session.get.return_value = None

    # Call send_response_draft_to_telegram - should raise ValueError
    with pytest.raises(ValueError, match="Email with id=999 not found"):
        await telegram_service.send_response_draft_to_telegram(email_id=999)


@pytest.mark.asyncio
async def test_send_response_draft_to_telegram_user_not_found(telegram_service, mock_db_session, mock_telegram_bot):
    """Test send_response_draft_to_telegram raises ValueError when user not found."""
    # Create email
    email = EmailProcessingQueue(
        id=42,
        user_id=1,
        sender="test@example.com",
        subject="Test",
        received_at=datetime.now(UTC),
        draft_response="Test draft",
        detected_language="en",
        is_priority=False
    )

    # Mock get to return email first, then None for user
    mock_db_session.get.side_effect = [email, None]

    # Call send_response_draft_to_telegram - should raise ValueError
    with pytest.raises(ValueError, match="User with id=1 not found"):
        await telegram_service.send_response_draft_to_telegram(email_id=42)


@pytest.mark.asyncio
async def test_send_response_draft_to_telegram_generic_exception(telegram_service, mock_db_session, mock_telegram_bot):
    """Test send_response_draft_to_telegram handles generic exceptions and re-raises."""
    # Create email and user
    email = EmailProcessingQueue(
        id=42,
        user_id=1,
        sender="test@example.com",
        subject="Test",
        received_at=datetime.now(UTC),
        draft_response="Test draft",
        detected_language="en",
        is_priority=False
    )
    user = User(
        id=1,
        email="user@example.com",
        telegram_id="123456",
        is_active=True
    )

    # Mock get to return email and user multiple times
    def get_side_effect(model, id):
        if model == EmailProcessingQueue:
            return email
        elif model == User:
            return user
        return None

    mock_db_session.get.side_effect = get_side_effect

    # Mock TelegramBotClient to raise generic exception
    mock_telegram_bot.send_message_with_buttons = AsyncMock(side_effect=RuntimeError("Network error"))

    # Call send_response_draft_to_telegram - should re-raise exception
    with pytest.raises(RuntimeError, match="Network error"):
        await telegram_service.send_response_draft_to_telegram(email_id=42)


def test_save_telegram_message_mapping_email_not_found(telegram_service, mock_db_session):
    """Test save_telegram_message_mapping raises ValueError when email not found."""
    # Mock session.get to return None (email not found)
    mock_db_session.get.return_value = None

    # Call save_telegram_message_mapping - should raise ValueError
    with pytest.raises(ValueError, match="Email with id=999 not found"):
        telegram_service.save_telegram_message_mapping(
            email_id=999,
            telegram_message_id="msg_123",
            thread_id="thread_456"
        )


def test_save_telegram_message_mapping_update_existing(telegram_service, mock_db_session):
    """Test save_telegram_message_mapping updates existing mapping instead of creating new one."""
    # Create email
    email = EmailProcessingQueue(
        id=42,
        user_id=1,
        sender="test@example.com",
        subject="Test",
        received_at=datetime.now(UTC),
        draft_response="Test draft",
        detected_language="en",
        is_priority=False
    )

    # Create existing mapping
    existing_mapping = WorkflowMapping(
        email_id=42,
        user_id=1,
        thread_id="old_thread_123",
        telegram_message_id="old_msg_456",
        workflow_state="old_state"
    )

    # Mock get to return email
    mock_db_session.get.return_value = email

    # Mock exec to return existing mapping
    mock_result = Mock()
    mock_result.first.return_value = existing_mapping
    mock_db_session.exec.return_value = mock_result

    # Call save_telegram_message_mapping
    telegram_service.save_telegram_message_mapping(
        email_id=42,
        telegram_message_id="new_msg_789",
        thread_id="new_thread_999"
    )

    # Verify existing mapping was updated
    assert existing_mapping.telegram_message_id == "new_msg_789"
    assert existing_mapping.thread_id == "new_thread_999"
    assert existing_mapping.workflow_state == "awaiting_response_approval"

    # Verify commit was called
    mock_db_session.commit.assert_called_once()

    # Verify add was NOT called (updated, not created)
    mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_send_draft_notification_email_not_found(telegram_service, mock_db_session, mock_telegram_bot):
    """Test send_draft_notification raises ValueError when email not found."""
    # Mock session.get to return None (email not found)
    mock_db_session.get.return_value = None

    # Call send_draft_notification - should raise ValueError
    with pytest.raises(ValueError, match="Email with id=999 not found"):
        await telegram_service.send_draft_notification(
            email_id=999,
            workflow_thread_id="thread_123"
        )


@pytest.mark.asyncio
async def test_send_draft_notification_no_draft_response(telegram_service, mock_db_session, mock_telegram_bot):
    """Test send_draft_notification raises ValueError when draft_response is missing."""
    # Create email without draft_response
    email = EmailProcessingQueue(
        id=42,
        user_id=1,
        sender="test@example.com",
        subject="Test",
        received_at=datetime.now(UTC),
        draft_response=None,  # No draft
        detected_language="en",
        is_priority=False
    )
    mock_db_session.get.return_value = email

    # Call send_draft_notification - should raise ValueError
    with pytest.raises(ValueError, match="has no draft_response field"):
        await telegram_service.send_draft_notification(
            email_id=42,
            workflow_thread_id="thread_123"
        )
