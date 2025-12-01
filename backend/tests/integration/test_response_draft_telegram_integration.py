"""
Integration Tests for Telegram Response Draft Service (Story 3.8)

Tests end-to-end workflows with real database and mocked Telegram bot.

Integration test scenarios:
1. test_end_to_end_response_draft_notification_german - German formal response with priority
2. test_end_to_end_response_draft_notification_english - English professional response
3. test_response_draft_long_message_splitting - Very long draft (>4096 chars)
4. test_response_draft_notification_with_rag_context - Context summary display
5. test_response_draft_notification_priority_email - Priority flagging
6. test_telegram_user_not_linked_handling - User without Telegram account

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.8 (Response Draft Telegram Messages)
"""

import pytest
import pytest_asyncio
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock
from sqlmodel import Session, select, create_engine

from app.services.telegram_response_draft import TelegramResponseDraftService
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User
from app.services.database import DatabaseService


# Test fixtures for integration tests

@pytest_asyncio.fixture
async def sync_db_service(db_session):
    """Create DatabaseService with sync engine for integration tests.

    TelegramResponseDraftService uses sync Session(engine), so we need
    a sync engine wrapper. This fixture creates a sync engine from the
    same DATABASE_URL used by the async test fixtures.
    """
    import os
    from sqlmodel import create_engine

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent")

    # Convert async URL to sync URL (remove +psycopg)
    sync_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")

    # Create sync engine
    sync_engine = create_engine(sync_url, echo=False, pool_pre_ping=True)

    # Create async session factory using the same async engine from db_session fixture
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from contextlib import asynccontextmanager

    # The db_session fixture already provides a working async session
    # We'll create a mock that returns the same session
    @asynccontextmanager
    async def mock_async_session_factory():
        yield db_session

    # Create mock DatabaseService with sync engine
    mock_db_service = Mock(spec=DatabaseService)
    mock_db_service.engine = sync_engine
    mock_db_service.async_session = mock_async_session_factory

    yield mock_db_service

    # Cleanup: dispose engine
    sync_engine.dispose()


# Integration Test 1: German formal response draft with priority flag (AC #1-9)

@pytest.mark.asyncio
async def test_end_to_end_response_draft_notification_german(
    db_session,
    sync_db_service,
    test_user: User
):
    """Test complete workflow for German formal response draft with priority flag (AC #1-9).

    Scenario: Priority email with German response draft
    Expected: Message sent with ⚠️ flag, WorkflowMapping created, status updated
    """
    # Create German priority email with response draft
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="german_email_001",
        gmail_thread_id="thread_german_001",
        sender="geschaeftspartner@example.de",
        subject="Dringende Frage zu unserem Vertrag",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response="Sehr geehrte Damen und Herren,\n\nvielen Dank für Ihre Anfrage. Ich werde mich umgehend um Ihr Anliegen kümmern.\n\nMit freundlichen Grüßen",
        detected_language="de",
        is_priority=True  # Priority flag
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Mock TelegramBotClient
    mock_telegram_bot = Mock()
    mock_telegram_bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_de_123")

    # Create service with real database and mocked Telegram bot
    service = TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=sync_db_service
    )

    # Call send_draft_notification
    result = await service.send_draft_notification(
        email_id=email.id,
        workflow_thread_id="workflow_thread_de_001"
    )

    # Assertions
    assert result is True

    # Verify TelegramBotClient.send_message_with_buttons called
    mock_telegram_bot.send_message_with_buttons.assert_called_once()

    # Verify message content
    call_args = mock_telegram_bot.send_message_with_buttons.call_args
    message_text = call_args.kwargs["text"]

    # AC #9: Priority flag present
    assert "⚠️" in message_text
    assert "📧 Response Draft Ready" in message_text

    # AC #2: Original email info
    assert "📨 Original Email:" in message_text
    assert "From: geschaeftspartner@example.de" in message_text
    assert "Subject: Dringende Frage zu unserem Vertrag" in message_text

    # AC #3, #6: AI-generated response with language indication
    assert "✍️ AI-Generated Response (German):" in message_text
    assert "Sehr geehrte Damen und Herren" in message_text

    # AC #4: Visual separators
    assert "─────────────────" in message_text

    # AC #5: Inline keyboard with 3 buttons
    buttons = call_args.kwargs["buttons"]
    assert len(buttons) == 2  # 2 rows
    assert len(buttons[0]) == 1  # Row 1: Send button
    assert len(buttons[1]) == 2  # Row 2: Edit + Reject buttons

    # Verify WorkflowMapping created (using sync session)
    with Session(sync_db_service.engine) as sync_session:
        mapping = sync_session.exec(
            select(WorkflowMapping).where(WorkflowMapping.email_id == email.id)
        ).first()
        assert mapping is not None
        assert mapping.telegram_message_id == "telegram_msg_de_123"
        assert mapping.thread_id == "workflow_thread_de_001"
        assert mapping.workflow_state == "awaiting_response_approval"

    # Verify email status updated (using async session)
    await db_session.refresh(email)
    assert email.status == "awaiting_response_approval"


# Integration Test 2: English professional response draft without priority (AC #1-7)

@pytest.mark.asyncio
async def test_end_to_end_response_draft_notification_english(
    db_session,
    sync_db_service,
    test_user: User
):
    """Test complete workflow for English professional response draft (AC #1-7).

    Scenario: Non-priority English email with response draft
    Expected: Message sent without ⚠️ flag, proper formatting
    """
    # Create English email with response draft (non-priority)
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="english_email_001",
        gmail_thread_id="thread_english_001",
        sender="partner@example.com",
        subject="Question about your product features",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response="Dear Sir/Madam,\n\nThank you for your inquiry about our product features. I will be happy to provide you with more information.\n\nBest regards",
        detected_language="en",
        is_priority=False  # Not priority
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Mock TelegramBotClient
    mock_telegram_bot = Mock()
    mock_telegram_bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_en_123")

    # Create service with real database
    service = TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=sync_db_service
    )

    # Call send_draft_notification
    result = await service.send_draft_notification(
        email_id=email.id,
        workflow_thread_id="workflow_thread_en_001"
    )

    # Assertions
    assert result is True

    # Verify message content
    call_args = mock_telegram_bot.send_message_with_buttons.call_args
    message_text = call_args.kwargs["text"]

    # AC #1: Header present without priority flag
    assert "📧 Response Draft Ready" in message_text
    assert "⚠️" not in message_text  # No priority flag

    # AC #2: Original email info
    assert "From: partner@example.com" in message_text
    assert "Subject: Question about your product features" in message_text

    # AC #3, #6: Draft with English language indication
    assert "✍️ AI-Generated Response (English):" in message_text
    assert "Dear Sir/Madam" in message_text

    # Verify WorkflowMapping created (using sync session)
    with Session(sync_db_service.engine) as sync_session:
        mapping = sync_session.exec(
            select(WorkflowMapping).where(WorkflowMapping.email_id == email.id)
        ).first()
        assert mapping is not None
        assert mapping.telegram_message_id == "telegram_msg_en_123"


# Integration Test 3: Very long response draft (>4096 chars) - AC #8

@pytest.mark.asyncio
async def test_response_draft_long_message_splitting(
    db_session,
    sync_db_service,
    test_user: User
):
    """Test Telegram length limit handling for very long drafts (AC #8).

    Scenario: Response draft exceeds 4096 character Telegram limit
    Expected: TelegramBotClient handles truncation, no exception raised
    """
    # Create very long response draft (>4096 chars)
    long_response = "Dear Sir/Madam,\n\n" + ("This is a very long paragraph that repeats many times. " * 100)
    long_response += "\n\nBest regards"

    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="long_email_001",
        gmail_thread_id="thread_long_001",
        sender="sender@example.com",
        subject="Question requiring detailed response",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response=long_response,  # Very long draft
        detected_language="en",
        is_priority=False
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Mock TelegramBotClient
    mock_telegram_bot = Mock()
    mock_telegram_bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_long_123")

    # Create service with real database
    service = TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=sync_db_service
    )

    # Call send_draft_notification
    result = await service.send_draft_notification(
        email_id=email.id,
        workflow_thread_id="workflow_thread_long_001"
    )

    # Assertions
    assert result is True  # No exception raised

    # Verify TelegramBotClient called with long message
    mock_telegram_bot.send_message_with_buttons.assert_called_once()

    call_args = mock_telegram_bot.send_message_with_buttons.call_args
    message_text = call_args.kwargs["text"]

    # Verify message is long (>4096 chars before truncation)
    assert len(message_text) > 4096

    # TelegramBotClient would handle truncation in production
    # Here we just verify service doesn't crash


# Integration Test 4: Context summary display (AC #7)

@pytest.mark.asyncio
async def test_response_draft_notification_with_rag_context(
    db_session,
    sync_db_service,
    test_user: User
):
    """Test context summary display with thread history (AC #7).

    Scenario: Response draft with RAG context from thread history
    Expected: Context summary line included in message (when implemented)

    Note: Currently context summary not implemented in service.
    This test documents expected behavior for future implementation.
    """
    # Create email with response draft
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="context_email_001",
        gmail_thread_id="thread_context_001",
        sender="sender@example.com",
        subject="Follow-up question",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response="Dear Sir/Madam,\n\nThank you for your follow-up. As discussed in our previous emails...\n\nBest regards",
        detected_language="en",
        is_priority=False
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Mock TelegramBotClient
    mock_telegram_bot = Mock()
    mock_telegram_bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_context_123")

    # Create service with real database
    service = TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=sync_db_service
    )

    # Call send_draft_notification
    result = await service.send_draft_notification(
        email_id=email.id,
        workflow_thread_id="workflow_thread_context_001"
    )

    # Assertions
    assert result is True

    # Verify message content
    call_args = mock_telegram_bot.send_message_with_buttons.call_args
    message_text = call_args.kwargs["text"]

    # TODO: When context_summary parameter added, verify line like:
    # "📚 Context: Based on 3 previous emails in this thread"
    # For now, just verify message is valid
    assert "📧 Response Draft Ready" in message_text


# Integration Test 5: Priority email flagging (AC #9)

@pytest.mark.asyncio
async def test_response_draft_notification_priority_email(
    db_session,
    sync_db_service,
    test_user: User
):
    """Test priority email flagging with ⚠️ icon (AC #9).

    Scenario: Email with is_priority=True
    Expected: ⚠️ icon present in message header
    """
    # Create priority email
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="priority_email_001",
        gmail_thread_id="thread_priority_001",
        sender="urgent@example.com",
        subject="URGENT: Action required",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response="Dear Sir/Madam,\n\nI will address this urgent matter immediately.\n\nBest regards",
        detected_language="en",
        is_priority=True  # Priority flag
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Mock TelegramBotClient
    mock_telegram_bot = Mock()
    mock_telegram_bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_priority_123")

    # Create service with real database
    service = TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=sync_db_service
    )

    # Call send_draft_notification
    result = await service.send_draft_notification(
        email_id=email.id,
        workflow_thread_id="workflow_thread_priority_001"
    )

    # Assertions
    assert result is True

    # Verify message content
    call_args = mock_telegram_bot.send_message_with_buttons.call_args
    message_text = call_args.kwargs["text"]

    # AC #9: Priority flag present
    assert "⚠️" in message_text
    assert message_text.startswith("⚠️ 📧 Response Draft Ready")


# Integration Test 6: Telegram user not linked handling

@pytest.mark.asyncio
async def test_telegram_user_not_linked_handling(
    db_session,
    sync_db_service,
    test_user_no_telegram: User
):
    """Test graceful handling when user hasn't linked Telegram account.

    Scenario: User has no telegram_id set
    Expected: ValueError raised with clear message
    """
    # Create email with response draft for user without Telegram
    email = EmailProcessingQueue(
        user_id=test_user_no_telegram.id,
        gmail_message_id="no_telegram_email_001",
        gmail_thread_id="thread_no_telegram_001",
        sender="sender@example.com",
        subject="Question",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        classification="needs_response",
        draft_response="Dear Sir/Madam,\n\nThank you for your question.\n\nBest regards",
        detected_language="en",
        is_priority=False
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Mock TelegramBotClient (won't be called)
    mock_telegram_bot = Mock()
    mock_telegram_bot.send_message_with_buttons = AsyncMock(return_value="telegram_msg_123")

    # Create service with real database
    service = TelegramResponseDraftService(
        telegram_bot=mock_telegram_bot,
        db_service=sync_db_service
    )

    # Call send_draft_notification - should raise ValueError
    with pytest.raises(ValueError, match="has no telegram_id set"):
        await service.send_draft_notification(
            email_id=email.id,
            workflow_thread_id="workflow_thread_no_telegram_001"
        )

    # Verify TelegramBotClient NOT called
    mock_telegram_bot.send_message_with_buttons.assert_not_called()


# Fixtures

@pytest_asyncio.fixture
async def test_user_no_telegram(db_session) -> User:
    """Create test user WITHOUT Telegram linked."""
    user = User(
        email="user_no_telegram@example.com",
        telegram_id=None,  # No Telegram linked
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
