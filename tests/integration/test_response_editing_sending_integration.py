"""
Integration Tests for Response Editing and Sending Services (Story 3.9)

Tests end-to-end workflows with real database and ChromaDB:
- AC #1-3: Complete edit workflow (button → reply → draft updated)
- AC #4-8: Send original and edited drafts via Gmail
- AC #6: Email threading (In-Reply-To headers)
- AC #9: Vector DB indexing for sent responses
- Reject workflow integration

Integration Test Strategy:
- Use real PostgreSQL test database
- Use real ChromaDB test instance for vector storage
- Mock TelegramBotClient (avoid real Telegram API calls)
- Mock GmailClient (avoid real Gmail API calls)
- Cleanup fixtures to remove test data after each test

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.9 (Response Editing and Sending)
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch
from sqlmodel import select
from telegram import Update, CallbackQuery, Message, User as TelegramUser
from telegram.ext import ContextTypes

from app.services.response_editing_service import ResponseEditingService
from app.services.response_sending_service import ResponseSendingService
from app.services.telegram_response_draft import TelegramResponseDraftService
from app.core.vector_db import VectorDBClient
from app.core.embedding_service import EmbeddingService
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest_asyncio.fixture
async def test_response_user(db_session):
    """Create test user for response editing/sending integration tests."""
    user = User(
        email="test_response@example.com",
        is_active=True,
        telegram_id="888888888",
        telegram_username="response_test_user",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC)
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user


@pytest_asyncio.fixture
async def test_response_email(db_session, test_response_user):
    """Create test email with response draft."""
    email = EmailProcessingQueue(
        user_id=test_response_user.id,
        gmail_message_id="test_msg_response_editing",
        gmail_thread_id="test_thread_response_editing",
        sender="sender@example.com",
        subject="Integration Test Email",
        received_at=datetime(2025, 11, 10, 10, 0, 0),
        status="awaiting_response_approval",
        classification="needs_response",
        draft_response="This is the original AI-generated response draft.",
        detected_language="en",
        tone="professional"
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    yield email


@pytest_asyncio.fixture
async def test_workflow_mapping(db_session, test_response_email):
    """Create test WorkflowMapping for callback routing."""
    mapping = WorkflowMapping(
        email_id=test_response_email.id,
        user_id=test_response_email.user_id,
        thread_id="workflow_test_thread_123",
        telegram_message_id="telegram_msg_456",
        workflow_state="awaiting_response_approval"
    )
    db_session.add(mapping)
    await db_session.commit()
    await db_session.refresh(mapping)
    yield mapping


@pytest.fixture
def test_response_vector_db():
    """Create VectorDBClient with test ChromaDB instance for sent response indexing."""
    test_persist_dir = "./data/chroma_test_response_editing"
    os.makedirs(test_persist_dir, exist_ok=True)

    vector_db = VectorDBClient(persist_directory=test_persist_dir)

    # Create test collection
    collection = vector_db.get_or_create_collection("email_embeddings")

    yield vector_db

    # Cleanup: Delete test collection and directory
    try:
        vector_db.delete_collection("email_embeddings")
    except Exception:
        pass


@pytest.fixture
def mock_telegram_bot_integration():
    """Mock TelegramBotClient for integration tests."""
    mock = AsyncMock()
    mock.send_message = AsyncMock(return_value="telegram_msg_789")
    mock.send_message_with_buttons = AsyncMock(return_value="telegram_msg_789")
    mock.initialize = AsyncMock()
    return mock


@pytest.fixture
def mock_gmail_client_integration():
    """Mock GmailClient for integration tests."""
    mock = AsyncMock()
    # Return sent message_id and capture threading parameters
    mock.send_email = AsyncMock(return_value="sent_gmail_msg_id_123")
    return mock


@pytest.fixture
def mock_callback_query_integration():
    """Create mock Telegram CallbackQuery for integration tests."""
    mock_query = Mock(spec=CallbackQuery)
    mock_query.from_user = Mock(spec=TelegramUser)
    mock_query.from_user.id = 888888888
    mock_query.data = "edit_response_123"
    mock_query.answer = AsyncMock()
    return mock_query


@pytest.fixture
def mock_message_integration():
    """Create mock Telegram Message for integration tests."""
    mock_msg = Mock(spec=Message)
    mock_msg.from_user = Mock(spec=TelegramUser)
    mock_msg.from_user.id = 888888888
    mock_msg.text = "This is my edited response for integration test."
    mock_msg.reply_text = AsyncMock()
    return mock_msg


@pytest.fixture
def mock_update_integration(mock_callback_query_integration, mock_message_integration):
    """Create mock Telegram Update for integration tests."""
    mock = Mock(spec=Update)
    mock.callback_query = mock_callback_query_integration
    mock.message = mock_message_integration
    mock.effective_user = mock_callback_query_integration.from_user
    return mock


@pytest.fixture
def mock_context_integration():
    """Create mock Telegram ContextTypes.DEFAULT_TYPE for integration tests."""
    mock = Mock(spec=ContextTypes.DEFAULT_TYPE)
    mock.bot_data = {}
    return mock


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_end_to_end_edit_workflow(
    db_session,
    test_response_user,
    test_response_email,
    test_workflow_mapping,
    mock_telegram_bot_integration,
    mock_update_integration,
    mock_context_integration
):
    """Test complete edit workflow from button click to draft updated (AC #1-3).

    End-to-end workflow:
    1. User clicks [Edit] button (AC #1)
    2. Bot sends prompt message (AC #1)
    3. User replies with edited text (AC #2)
    4. Draft updated in database (AC #3)
    5. WorkflowMapping.workflow_state = "draft_edited"
    6. Confirmation message sent
    """
    # Setup services
    draft_service = Mock(spec=TelegramResponseDraftService)
    draft_service.send_response_draft = AsyncMock()

    editing_service = ResponseEditingService(
        telegram_bot=mock_telegram_bot_integration,
        draft_service=draft_service
    )

    # Execute: Handle edit button click (AC #1)
    await editing_service.handle_edit_response_callback(
        update=mock_update_integration,
        context=mock_context_integration,
        email_id=test_response_email.id,
        user_id=test_response_user.id
    )

    # Verify: Prompt message sent (AC #1)
    mock_telegram_bot_integration.send_message.assert_called_once()
    prompt_text = mock_telegram_bot_integration.send_message.call_args.kwargs["text"]
    assert "Edit Response Draft" in prompt_text

    # Verify: Editing session stored
    from app.services.response_editing_service import _edit_sessions
    assert "888888888" in _edit_sessions

    # Execute: Handle user reply message (AC #2)
    await editing_service.handle_message_reply(
        update=mock_update_integration,
        context=mock_context_integration
    )

    # Verify: Draft updated in real database (AC #3)
    await db_session.refresh(test_response_email)
    assert test_response_email.draft_response == "This is my edited response for integration test."
    assert test_response_email.status == "draft_edited"

    # Verify: WorkflowMapping state updated
    await db_session.refresh(test_workflow_mapping)
    assert test_workflow_mapping.workflow_state == "draft_edited"

    # Verify: Confirmation sent (AC #2)
    mock_update_integration.message.reply_text.assert_called_once()

    # Verify: Draft re-sent
    draft_service.send_response_draft.assert_called_once()

    # Verify: Editing session cleared
    assert "888888888" not in _edit_sessions


@pytest.mark.asyncio
async def test_end_to_end_send_original_draft(
    db_session,
    test_response_user,
    test_response_email,
    test_workflow_mapping,
    test_response_vector_db,
    mock_telegram_bot_integration,
    mock_gmail_client_integration,
    mock_update_integration,
    mock_context_integration
):
    """Test send original draft end-to-end workflow (AC #4-8).

    End-to-end workflow:
    1. User clicks [Send] button on original draft (AC #4)
    2. Gmail API called with original draft (AC #5)
    3. Email threaded correctly (AC #6)
    4. Email status = "completed" (AC #8)
    5. Telegram confirmation sent (AC #7)
    """
    # Setup services
    embedding_service = EmbeddingService()

    sending_service = ResponseSendingService(
        telegram_bot=mock_telegram_bot_integration,
        embedding_service=embedding_service,
        vector_db_client=test_response_vector_db
    )

    # Execute: Handle send button click
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client_integration):
        await sending_service.handle_send_response_callback(
            update=mock_update_integration,
            context=mock_context_integration,
            email_id=test_response_email.id,
            user_id=test_response_user.id
        )

    # Verify: Gmail send called with original draft (AC #4, #5)
    mock_gmail_client_integration.send_email.assert_called_once()
    call_args = mock_gmail_client_integration.send_email.call_args
    assert call_args.kwargs["to"] == "sender@example.com"
    assert call_args.kwargs["subject"] == "Re: Integration Test Email"
    assert call_args.kwargs["body"] == "This is the original AI-generated response draft."

    # Verify: Threading parameter passed (AC #6)
    assert call_args.kwargs["thread_id"] == "test_thread_response_editing"

    # Verify: Email status updated in real database (AC #8)
    await db_session.refresh(test_response_email)
    assert test_response_email.status == "completed"

    # Verify: WorkflowMapping state updated
    await db_session.refresh(test_workflow_mapping)
    assert test_workflow_mapping.workflow_state == "sent"

    # Verify: Telegram confirmation sent (AC #7)
    confirmation_calls = [
        call for call in mock_telegram_bot_integration.send_message.call_args_list
        if "Response sent to" in call.kwargs.get("text", "")
    ]
    assert len(confirmation_calls) == 1
    confirmation_text = confirmation_calls[0].kwargs["text"]
    assert "sender@example.com" in confirmation_text


@pytest.mark.asyncio
async def test_end_to_end_send_edited_draft(
    db_session,
    test_response_user,
    test_response_email,
    test_workflow_mapping,
    test_response_vector_db,
    mock_telegram_bot_integration,
    mock_gmail_client_integration,
    mock_update_integration,
    mock_context_integration
):
    """Test send edited draft end-to-end workflow (AC #4-8).

    End-to-end workflow:
    1. Draft is edited first (update draft_response)
    2. User clicks [Send] button on edited draft (AC #4)
    3. Gmail API called with edited draft (AC #5)
    4. Email status = "completed" (AC #8)
    5. Telegram confirmation sent (AC #7)
    """
    # Setup: Edit draft first
    test_response_email.draft_response = "This is the EDITED draft for integration test."
    test_response_email.status = "draft_edited"
    db_session.add(test_response_email)
    await db_session.commit()

    # Setup services
    embedding_service = EmbeddingService()

    sending_service = ResponseSendingService(
        telegram_bot=mock_telegram_bot_integration,
        embedding_service=embedding_service,
        vector_db_client=test_response_vector_db
    )

    # Execute: Handle send button click
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client_integration):
        await sending_service.handle_send_response_callback(
            update=mock_update_integration,
            context=mock_context_integration,
            email_id=test_response_email.id,
            user_id=test_response_user.id
        )

    # Verify: Gmail send called with EDITED draft (AC #4, #5)
    mock_gmail_client_integration.send_email.assert_called_once()
    call_args = mock_gmail_client_integration.send_email.call_args
    assert call_args.kwargs["body"] == "This is the EDITED draft for integration test."

    # Verify: Email status updated in real database (AC #8)
    await db_session.refresh(test_response_email)
    assert test_response_email.status == "completed"


@pytest.mark.asyncio
async def test_email_threading_in_reply(
    db_session,
    test_response_user,
    test_response_email,
    test_workflow_mapping,
    test_response_vector_db,
    mock_telegram_bot_integration,
    mock_gmail_client_integration,
    mock_update_integration,
    mock_context_integration
):
    """Test In-Reply-To and References headers in sent email (AC #6).

    Verifies that threading parameters:
    1. thread_id passed to GmailClient.send_email()
    2. GmailClient handles In-Reply-To and References headers
    3. Email appears in correct Gmail thread
    """
    # Setup services
    embedding_service = EmbeddingService()

    sending_service = ResponseSendingService(
        telegram_bot=mock_telegram_bot_integration,
        embedding_service=embedding_service,
        vector_db_client=test_response_vector_db
    )

    # Execute: Send email
    with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client_integration):
        await sending_service.handle_send_response_callback(
            update=mock_update_integration,
            context=mock_context_integration,
            email_id=test_response_email.id,
            user_id=test_response_user.id
        )

    # Verify: thread_id parameter passed (AC #6)
    mock_gmail_client_integration.send_email.assert_called_once()
    call_args = mock_gmail_client_integration.send_email.call_args
    assert "thread_id" in call_args.kwargs
    assert call_args.kwargs["thread_id"] == "test_thread_response_editing"

    # Note: GmailClient.send_email() implementation (Story 1.9) automatically
    # handles In-Reply-To and References headers based on thread_id parameter


@pytest.mark.asyncio
async def test_sent_response_indexed_to_chromadb(
    db_session,
    test_response_user,
    test_response_email,
    test_workflow_mapping,
    test_response_vector_db,
    mock_telegram_bot_integration,
    mock_gmail_client_integration,
    mock_update_integration,
    mock_context_integration
):
    """Test sent response indexed to ChromaDB for future RAG (AC #9).

    Verifies that after successful send:
    1. Embedding generated for sent response
    2. Embedding stored in ChromaDB "email_embeddings" collection
    3. Metadata includes: message_id, user_id, thread_id, sender, subject, date, language
    4. Sent response appears in ChromaDB for future retrieval
    """
    # Setup services
    embedding_service = EmbeddingService()

    sending_service = ResponseSendingService(
        telegram_bot=mock_telegram_bot_integration,
        embedding_service=embedding_service,
        vector_db_client=test_response_vector_db
    )

    # Execute: Send email (which triggers indexing)
    with patch('app.services.response_sending_service.Session') as mock_session_cls:
        mock_session = Mock()
        mock_session_cls.return_value.__enter__.return_value = db_session
        mock_session_cls.return_value.__exit__.return_value = None

        with patch('app.services.response_sending_service.GmailClient', return_value=mock_gmail_client_integration):
            await sending_service.handle_send_response_callback(
                update=mock_update_integration,
                context=mock_context_integration,
                email_id=test_response_email.id,
                user_id=test_response_user.id
            )

    # Verify: Sent response indexed in ChromaDB (AC #9)
    collection = test_response_vector_db.get_or_create_collection("email_embeddings")

    # Query collection to verify embedding exists
    results = collection.get(
        where={"$and": [{"user_id": test_response_user.id}, {"is_sent_response": True}]},
        include=["metadatas", "embeddings"]
    )

    assert len(results["ids"]) >= 1, "Sent response should be indexed"

    # Verify metadata structure (AC #9) - check the most recent entry
    # Find the most recent entry by checking IDs (sent_{email_id}_{timestamp})
    metadata = results["metadatas"][-1]  # Most recent entry
    assert metadata["user_id"] == test_response_user.id
    assert metadata["thread_id"] == "test_thread_response_editing"
    assert metadata["sender"] == "sender@example.com"
    assert "Re: Integration Test Email" in metadata["subject"]
    assert metadata["language"] == "en"
    assert metadata["is_sent_response"] is True

    # Verify embedding dimensions (768 for Gemini text-embedding-004)
    embedding = results["embeddings"][0]
    assert len(embedding) == 768


@pytest.mark.asyncio
async def test_reject_response_workflow(
    db_session,
    test_response_user,
    test_response_email,
    test_workflow_mapping,
    test_response_vector_db,
    mock_telegram_bot_integration,
    mock_update_integration,
    mock_context_integration
):
    """Test reject button marks email as rejected.

    End-to-end reject workflow:
    1. User clicks [Reject] button
    2. Email status = "rejected"
    3. WorkflowMapping.workflow_state = "rejected"
    4. Telegram confirmation sent
    5. No Gmail API call made
    """
    # Setup services
    embedding_service = EmbeddingService()

    sending_service = ResponseSendingService(
        telegram_bot=mock_telegram_bot_integration,
        embedding_service=embedding_service,
        vector_db_client=test_response_vector_db
    )

    # Execute: Handle reject button click
    await sending_service.handle_reject_response_callback(
        update=mock_update_integration,
        context=mock_context_integration,
        email_id=test_response_email.id,
        user_id=test_response_user.id
    )

    # Verify: Email status updated in real database
    await db_session.refresh(test_response_email)
    assert test_response_email.status == "rejected"

    # Verify: WorkflowMapping state updated
    await db_session.refresh(test_workflow_mapping)
    assert test_workflow_mapping.workflow_state == "rejected"

    # Verify: Telegram confirmation sent
    mock_telegram_bot_integration.send_message.assert_called_once()
    confirmation_text = mock_telegram_bot_integration.send_message.call_args.kwargs["text"]
    assert "Response draft rejected" in confirmation_text
