"""Unit tests for send_email_response idempotency (Story 2.1)."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.nodes import send_email_response
from app.models.email import EmailProcessingQueue
from app.core.gmail_client import GmailClient


@pytest.fixture
def mock_email():
    """Create a mock email for testing."""
    email = EmailProcessingQueue(
        id=1,
        user_id=1,
        gmail_message_id="msg_123",
        gmail_thread_id="thread_456",
        sender="sender@example.com",
        subject="Test Subject",
        received_at=datetime.now(UTC),
        status="approved",
        classification="needs_response",
        draft_response="This is a draft response",
        email_sent_at=None,  # Not yet sent
    )
    return email


@pytest.fixture
def mock_email_already_sent():
    """Create a mock email that was already sent."""
    email = EmailProcessingQueue(
        id=2,
        user_id=1,
        gmail_message_id="msg_456",
        gmail_thread_id="thread_789",
        sender="sender2@example.com",
        subject="Already Sent",
        received_at=datetime.now(UTC) - timedelta(hours=1),
        status="response_sent",
        classification="needs_response",
        draft_response="This was already sent",
        email_sent_at=datetime.now(UTC) - timedelta(minutes=30),  # Already sent
    )
    return email


@pytest.fixture
def workflow_state():
    """Create a mock workflow state."""
    return {
        "email_id": "1",
        "classification": "needs_response",
        "user_decision": "approve",
        "draft_response": "This is a draft response",
    }


@pytest.mark.asyncio
async def test_send_email_response_first_time_success(mock_email, workflow_state):
    """Test that email is sent successfully the first time."""
    # Create mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_email
    mock_db.execute.return_value = mock_result

    # Create mock db_factory that returns our mock session
    @asynccontextmanager
    async def mock_db_factory():
        yield mock_db

    # Create mock Gmail client
    mock_gmail = AsyncMock(spec=GmailClient)
    mock_gmail.send_email.return_value = "sent_msg_123"

    # Execute the node
    result = await send_email_response(
        state=workflow_state,
        db_factory=mock_db_factory,
        gmail_client=mock_gmail
    )

    # Assertions
    assert result["sent_message_id"] == "sent_msg_123"
    assert mock_email.status == "response_sent"
    assert mock_email.email_sent_at is not None
    assert isinstance(mock_email.email_sent_at, datetime)

    # Verify Gmail send was called once
    mock_gmail.send_email.assert_called_once()
    call_args = mock_gmail.send_email.call_args
    assert call_args.kwargs["to"] == "sender@example.com"
    assert call_args.kwargs["subject"] == "Re: Test Subject"
    assert call_args.kwargs["body"] == "This is a draft response"
    assert call_args.kwargs["thread_id"] == "thread_456"

    # Verify database commit was called
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_send_email_response_idempotency_skip_duplicate(mock_email_already_sent):
    """Test that email is NOT sent if email_sent_at is already set (idempotency)."""
    # Create workflow state for already-sent email
    workflow_state = {
        "email_id": "2",
        "classification": "needs_response",
        "user_decision": "approve",
        "draft_response": "This was already sent",
    }

    # Create mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_email_already_sent
    mock_db.execute.return_value = mock_result

    # Create mock db_factory
    @asynccontextmanager
    async def mock_db_factory():
        yield mock_db

    # Create mock Gmail client
    mock_gmail = AsyncMock(spec=GmailClient)

    # Store original email_sent_at value
    original_sent_at = mock_email_already_sent.email_sent_at

    # Execute the node
    result = await send_email_response(
        state=workflow_state,
        db_factory=mock_db_factory,
        gmail_client=mock_gmail
    )

    # Assertions - email should NOT be sent again
    assert "sent_message_id" not in result or result.get("sent_message_id") is None
    assert mock_email_already_sent.email_sent_at == original_sent_at  # Unchanged

    # Verify Gmail send was NOT called (idempotency!)
    mock_gmail.send_email.assert_not_called()

    # Verify database was NOT modified
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_response_skip_if_not_needs_response():
    """Test that email is skipped if classification is not 'needs_response'."""
    workflow_state = {
        "email_id": "3",
        "classification": "sort_only",  # NOT needs_response
        "user_decision": "approve",
        "draft_response": "This should not be sent",
    }

    # Create mock db_factory
    @asynccontextmanager
    async def mock_db_factory():
        yield AsyncMock(spec=AsyncSession)

    # Create mock Gmail client
    mock_gmail = AsyncMock(spec=GmailClient)

    # Execute the node
    result = await send_email_response(
        state=workflow_state,
        db_factory=mock_db_factory,
        gmail_client=mock_gmail
    )

    # Assertions - email should be skipped
    assert "sent_message_id" not in result or result.get("sent_message_id") is None
    mock_gmail.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_response_skip_if_not_approved():
    """Test that email is skipped if user_decision is not 'approve'."""
    workflow_state = {
        "email_id": "4",
        "classification": "needs_response",
        "user_decision": "reject",  # NOT approve
        "draft_response": "This should not be sent",
    }

    # Create mock db_factory
    @asynccontextmanager
    async def mock_db_factory():
        yield AsyncMock(spec=AsyncSession)

    # Create mock Gmail client
    mock_gmail = AsyncMock(spec=GmailClient)

    # Execute the node
    result = await send_email_response(
        state=workflow_state,
        db_factory=mock_db_factory,
        gmail_client=mock_gmail
    )

    # Assertions - email should be skipped
    assert "sent_message_id" not in result or result.get("sent_message_id") is None
    mock_gmail.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_response_multiple_calls_same_email(mock_email, workflow_state):
    """Test that calling send_email_response twice on the same email only sends once."""
    # Create mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_email
    mock_db.execute.return_value = mock_result

    # Create mock db_factory
    @asynccontextmanager
    async def mock_db_factory():
        yield mock_db

    # Create mock Gmail client
    mock_gmail = AsyncMock(spec=GmailClient)
    mock_gmail.send_email.return_value = "sent_msg_123"

    # First call - should send email
    result1 = await send_email_response(
        state=workflow_state,
        db_factory=mock_db_factory,
        gmail_client=mock_gmail
    )

    assert result1["sent_message_id"] == "sent_msg_123"
    assert mock_email.email_sent_at is not None
    assert mock_gmail.send_email.call_count == 1

    # Reset mock to track second call
    mock_gmail.send_email.reset_mock()

    # Second call - should NOT send email (idempotency)
    result2 = await send_email_response(
        state=workflow_state,
        db_factory=mock_db_factory,
        gmail_client=mock_gmail
    )

    # Verify second call did NOT send email
    mock_gmail.send_email.assert_not_called()
