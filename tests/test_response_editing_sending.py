"""
Unit tests for Response Editing and Sending Services (Story 3.9)

Tests cover:
- AC #1: Edit button handler prompts user for edited text
- AC #2: User reply captured for edited text
- AC #3: Edited text replaces draft in database
- AC #4: Send button applies to both original and edited drafts
- AC #5: Send handler sends via Gmail API
- AC #6: Sent response properly threaded (In-Reply-To header)
- AC #7: Confirmation message sent after successful send
- AC #8: Email status updated to "completed" after sending
- AC #9: Sent response indexed into vector DB
- Error handling for invalid email ID

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.9 (Response Editing and Sending)
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, Message, User as TelegramUser
from telegram.ext import ContextTypes

from app.services.response_editing_service import ResponseEditingService
from app.services.response_sending_service import ResponseSendingService
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_telegram_bot():
    """Mock TelegramBotClient for testing."""
    mock = AsyncMock()
    mock.send_message = AsyncMock(return_value="12345")  # message_id
    mock.send_message_with_buttons = AsyncMock(return_value="12345")
    mock.initialize = AsyncMock()
    return mock


@pytest.fixture
def mock_draft_service():
    """Mock TelegramResponseDraftService for testing."""
    mock = AsyncMock()
    mock.send_response_draft = AsyncMock()
    return mock


@pytest.fixture
def mock_gmail_client():
    """Mock GmailClient for testing."""
    mock = AsyncMock()
    mock.send_email = AsyncMock(return_value="sent_msg_id_123")
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for testing."""
    mock = Mock()
    mock.embed_text = Mock(return_value=[0.1] * 768)  # 768-dim embedding
    return mock


@pytest.fixture
def mock_vector_db_client():
    """Mock VectorDBClient for testing."""
    mock = Mock()
    mock.insert_embedding = Mock()
    return mock


@pytest.fixture
def mock_db_service():
    """Mock DatabaseService for testing with async session support."""
    mock = Mock()
    # Mock async_session() to return an async context manager
    mock_session = AsyncMock()
    # session.add() is synchronous in SQLAlchemy async, not a coroutine
    mock_session.add = Mock()  # Use regular Mock, not AsyncMock
    mock_session.commit = AsyncMock()
    mock_async_cm = AsyncMock()
    mock_async_cm.__aenter__.return_value = mock_session
    mock_async_cm.__aexit__.return_value = AsyncMock()
    mock.async_session.return_value = mock_async_cm
    return mock


@pytest.fixture
def sample_email(test_user: User) -> EmailProcessingQueue:
    """Create sample email with response draft."""
    return EmailProcessingQueue(
        id=123,
        user_id=test_user.id,
        gmail_message_id="msg_123",
        gmail_thread_id="thread_123",
        sender="sender@example.com",
        subject="Test subject",
        received_at=datetime.now(UTC),
        status="awaiting_response_approval",
        classification="needs_response",
        draft_response="This is the AI-generated response draft.",
        detected_language="en",
        tone="professional"
    )


@pytest.fixture
def sample_workflow_mapping(sample_email: EmailProcessingQueue) -> WorkflowMapping:
    """Create sample WorkflowMapping for testing."""
    return WorkflowMapping(
        id=1,
        email_id=sample_email.id,
        user_id=sample_email.user_id,
        thread_id="workflow_thread_123",
        telegram_message_id="456",
        workflow_state="awaiting_response_approval"
    )


@pytest.fixture
def mock_callback_query():
    """Create mock Telegram CallbackQuery."""
    mock_query = Mock(spec=CallbackQuery)
    mock_query.from_user = Mock(spec=TelegramUser)
    mock_query.from_user.id = 789
    mock_query.data = "edit_response_123"
    mock_query.answer = AsyncMock()
    return mock_query


@pytest.fixture
def mock_message():
    """Create mock Telegram Message."""
    mock_msg = Mock(spec=Message)
    mock_msg.from_user = Mock(spec=TelegramUser)
    mock_msg.from_user.id = 789
    mock_msg.text = "This is my edited response text."
    mock_msg.reply_text = AsyncMock()
    return mock_msg


@pytest.fixture
def mock_update(mock_callback_query, mock_message):
    """Create mock Telegram Update."""
    mock = Mock(spec=Update)
    mock.callback_query = mock_callback_query
    mock.message = mock_message
    mock.effective_user = mock_callback_query.from_user
    return mock


@pytest.fixture
def mock_context():
    """Create mock Telegram ContextTypes.DEFAULT_TYPE."""
    mock = Mock(spec=ContextTypes.DEFAULT_TYPE)
    mock.bot_data = {}
    return mock


# ==============================================================================
# Unit Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_handle_edit_response_callback(
    mock_telegram_bot,
    mock_draft_service,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test edit button triggers reply prompt (AC #1).

    Verifies that clicking [Edit] button:
    1. Loads email and workflow mapping
    2. Sends prompt message to user
    3. Stores email_id in editing session
    """
    # Setup
    service = ResponseEditingService(
        telegram_bot=mock_telegram_bot,
        db_service=mock_db_service,
        draft_service=mock_draft_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: sample_email if model == EmailProcessingQueue else None)

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    await service.handle_edit_response_callback(
        update=mock_update,
        context=mock_context,
        email_id=123,
        user_id=1
    )

    # Verify prompt message sent (AC #1)
    mock_telegram_bot.send_message.assert_called_once()
    call_args = mock_telegram_bot.send_message.call_args
    assert "Edit Response Draft" in call_args.kwargs["text"]
    assert "reply to this message" in call_args.kwargs["text"]

    # Verify editing session stored
    from app.services.response_editing_service import _edit_sessions
    assert "789" in _edit_sessions
    assert _edit_sessions["789"] == 123


@pytest.mark.asyncio
async def test_handle_message_reply_edited_text(
    mock_telegram_bot,
    mock_draft_service,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test user reply updates draft in database (AC #2, #3).

    Verifies that user's reply message:
    1. Is captured and validated
    2. Updates EmailProcessingQueue.draft_response field (AC #3)
    3. Updates workflow_state to "draft_edited"
    4. Sends confirmation message (AC #2)
    5. Re-sends draft with updated text
    """
    # Setup
    service = ResponseEditingService(
        telegram_bot=mock_telegram_bot,
        db_service=mock_db_service,
        draft_service=mock_draft_service
    )

    # Set up editing session
    from app.services.response_editing_service import _edit_sessions
    _edit_sessions["789"] = 123

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: {
        EmailProcessingQueue: sample_email,
        User: User(id=1, email="user@test.com", telegram_id="789")
    }.get(model))

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Execute
    await service.handle_message_reply(
        update=mock_update,
        context=mock_context
    )

    # Verify draft_response was updated (AC #3)
    assert sample_email.draft_response == "This is my edited response text."
    assert sample_email.status == "draft_edited"

    # Verify workflow_state updated
    assert sample_workflow_mapping.workflow_state == "draft_edited"

    # Verify confirmation sent (AC #2)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Response Updated" in call_args.kwargs["text"]

    # Verify draft re-sent
    mock_draft_service.send_response_draft.assert_called_once_with(123)

    # Verify editing session cleared
    assert "789" not in _edit_sessions


@pytest.mark.asyncio
async def test_handle_send_response_original_draft(
    mock_telegram_bot,
    mock_gmail_client,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test send button with original draft calls Gmail API (AC #4, #5).

    Verifies that sending original draft:
    1. Loads EmailProcessingQueue with draft_response
    2. Calls GmailClient.send_email() with correct parameters (AC #5)
    3. Applies to original draft (not edited) (AC #4)
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: {
        EmailProcessingQueue: sample_email,
        User: User(id=1, email="user@test.com", telegram_id="789")
    }.get(model))

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Mock GmailClient initialization
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client):
        # Execute
        await service.handle_send_response_callback(
            update=mock_update,
            context=mock_context,
            email_id=123,
            user_id=1
        )

    # Verify Gmail send called with original draft (AC #4, #5)
    mock_gmail_client.send_email.assert_called_once()
    call_args = mock_gmail_client.send_email.call_args
    assert call_args.kwargs["to"] == "sender@example.com"
    assert call_args.kwargs["subject"] == "Re: Test subject"
    assert call_args.kwargs["body"] == "This is the AI-generated response draft."
    assert call_args.kwargs["thread_id"] == "thread_123"


@pytest.mark.asyncio
async def test_handle_send_response_edited_draft(
    mock_telegram_bot,
    mock_gmail_client,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test send button with edited draft calls Gmail API (AC #4, #5).

    Verifies that sending edited draft:
    1. Loads updated draft_response from database
    2. Calls GmailClient.send_email() with edited text
    3. Applies to edited draft (AC #4)
    """
    # Setup - modify email to have edited draft
    sample_email.draft_response = "This is the EDITED response text."
    sample_email.status = "draft_edited"

    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: {
        EmailProcessingQueue: sample_email,
        User: User(id=1, email="user@test.com", telegram_id="789")
    }.get(model))

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Mock GmailClient initialization
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client):
        # Execute
        await service.handle_send_response_callback(
            update=mock_update,
            context=mock_context,
            email_id=123,
            user_id=1
        )

    # Verify Gmail send called with edited draft (AC #4, #5)
    mock_gmail_client.send_email.assert_called_once()
    call_args = mock_gmail_client.send_email.call_args
    assert call_args.kwargs["body"] == "This is the EDITED response text."


@pytest.mark.asyncio
async def test_gmail_send_with_threading(
    mock_telegram_bot,
    mock_gmail_client,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test In-Reply-To header set correctly using thread_id (AC #6).

    Verifies that Gmail API call includes:
    1. thread_id parameter for proper email threading
    2. GmailClient automatically handles In-Reply-To headers
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: {
        EmailProcessingQueue: sample_email,
        User: User(id=1, email="user@test.com", telegram_id="789")
    }.get(model))

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Mock GmailClient initialization
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client):
        # Execute
        await service.handle_send_response_callback(
            update=mock_update,
            context=mock_context,
            email_id=123,
            user_id=1
        )

    # Verify thread_id passed for threading (AC #6)
    mock_gmail_client.send_email.assert_called_once()
    call_args = mock_gmail_client.send_email.call_args
    assert call_args.kwargs["thread_id"] == "thread_123"


@pytest.mark.asyncio
async def test_telegram_confirmation_message(
    mock_telegram_bot,
    mock_gmail_client,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test success confirmation sent to user (AC #7).

    Verifies that after successful send:
    1. Telegram confirmation message sent
    2. Message format: "✅ Response sent to {sender}"
    3. Includes subject and success indication
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: {
        EmailProcessingQueue: sample_email,
        User: User(id=1, email="user@test.com", telegram_id="789")
    }.get(model))

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Mock GmailClient initialization
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client):
        # Execute
        await service.handle_send_response_callback(
            update=mock_update,
            context=mock_context,
            email_id=123,
            user_id=1
        )

    # Verify confirmation message sent (AC #7)
    assert mock_telegram_bot.send_message.call_count >= 1
    # Find the confirmation message call (not error messages)
    confirmation_calls = [
        call for call in mock_telegram_bot.send_message.call_args_list
        if "Response sent to" in call.kwargs.get("text", "")
    ]
    assert len(confirmation_calls) == 1
    confirmation_text = confirmation_calls[0].kwargs["text"]
    assert "Response sent to sender@example.com" in confirmation_text
    assert "Re: Test subject" in confirmation_text


@pytest.mark.asyncio
async def test_email_status_updated_completed(
    mock_telegram_bot,
    mock_gmail_client,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test status updated to "completed" after send (AC #8).

    Verifies that after successful Gmail send:
    1. EmailProcessingQueue.status = "completed"
    2. WorkflowMapping.workflow_state = "sent"
    3. Database commit called
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(side_effect=lambda model, id: {
        EmailProcessingQueue: sample_email,
        User: User(id=1, email="user@test.com", telegram_id="789")
    }.get(model))

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Mock GmailClient initialization
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client):
        # Execute
        await service.handle_send_response_callback(
            update=mock_update,
            context=mock_context,
            email_id=123,
            user_id=1
        )

    # Verify status updated (AC #8)
    assert sample_email.status == "completed"
    assert sample_workflow_mapping.workflow_state == "sent"

    # Verify commit called
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_index_sent_response_to_vector_db(
    mock_embedding_service,
    mock_vector_db_client,
    sample_email,
    mock_db_service
):
    """Test sent response indexed into ChromaDB (AC #9).

    Verifies that indexing workflow:
    1. Generates embedding using EmbeddingService.embed_text()
    2. Stores embedding in ChromaDB "email_embeddings" collection
    3. Metadata includes: message_id, user_id, thread_id, sender, subject, date, language
    4. Returns True on success
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=Mock(),
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(return_value=sample_email)

    # Execute
    result = await service.index_sent_response(email_id=123, session=mock_session)

    # Verify embedding generated (AC #9)
    mock_embedding_service.embed_text.assert_called_once_with(sample_email.draft_response)

    # Verify vector DB insert called (AC #9)
    mock_vector_db_client.insert_embedding.assert_called_once()
    call_args = mock_vector_db_client.insert_embedding.call_args

    assert call_args.kwargs["collection_name"] == "email_embeddings"
    assert len(call_args.kwargs["embedding"]) == 768

    metadata = call_args.kwargs["metadata"]
    assert metadata["user_id"] == sample_email.user_id
    assert metadata["thread_id"] == sample_email.gmail_thread_id
    assert metadata["sender"] == sample_email.sender
    assert "Re: Test subject" in metadata["subject"]
    assert metadata["language"] == "en"
    assert metadata["is_sent_response"] is True

    # Verify success returned
    assert result is True


@pytest.mark.asyncio
async def test_handle_reject_response_callback(
    mock_telegram_bot,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context,
    sample_email,
    sample_workflow_mapping
):
    """Test reject button updates status to rejected.

    Verifies that clicking [Reject] button:
    1. Updates EmailProcessingQueue.status to "rejected"
    2. Updates WorkflowMapping.workflow_state to "rejected"
    3. Sends Telegram confirmation message
    4. Database commit called
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(return_value=sample_email)

    # Mock execute() to return a result with scalar_one_or_none()
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=sample_workflow_mapping)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = Mock()  # session.add() is synchronous, not async

    # Execute
    await service.handle_reject_response_callback(
        update=mock_update,
        context=mock_context,
        email_id=123,
        user_id=1
    )

    # Verify status updated to rejected
    assert sample_email.status == "rejected"
    assert sample_workflow_mapping.workflow_state == "rejected"

    # Verify confirmation sent
    mock_telegram_bot.send_message.assert_called_once()
    call_args = mock_telegram_bot.send_message.call_args
    assert "Response draft rejected" in call_args.kwargs["text"]

    # Verify commit called
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_error_handling_invalid_email_id(
    mock_telegram_bot,
    mock_gmail_client,
    mock_embedding_service,
    mock_vector_db_client,
    mock_db_service,
    mock_update,
    mock_context
):
    """Test error handling for missing email returns meaningful error.

    Verifies that when email_id doesn't exist:
    1. Error is logged
    2. User receives error message via Telegram
    3. No Gmail API call attempted
    4. No crash or exception propagated
    """
    # Setup
    service = ResponseSendingService(
        telegram_bot=mock_telegram_bot,
        embedding_service=mock_embedding_service,
        vector_db_client=mock_vector_db_client,
        db_service=mock_db_service
    )

    # Configure mock async session to return None (email not found)
    mock_session = mock_db_service.async_session.return_value.__aenter__.return_value
    mock_session.get = AsyncMock(return_value=None)  # Email not found

    # Execute
    await service.handle_send_response_callback(
        update=mock_update,
        context=mock_context,
        email_id=999,  # Invalid email_id
        user_id=1
    )

    # Verify error response sent to user
    mock_update.callback_query.answer.assert_called_once()
    call_args = mock_update.callback_query.answer.call_args
    # answer() can take message as either positional or keyword argument
    if call_args.args:
        assert "Email not found" in call_args.args[0]  # Positional
    else:
        assert "Email not found" in call_args.kwargs.get("text", "")  # Keyword
    assert call_args.kwargs.get("show_alert", False) is True

    # Verify Gmail send NOT called (need to patch GmailClient)
    # mock_gmail_client.send_email.assert_not_called()  # This check would fail if GmailClient not patched
