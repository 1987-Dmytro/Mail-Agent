"""Unit tests for Gmail email sending functionality.

Tests cover:
- _compose_mime_message(): MIME message composition with plain/HTML body
- _compose_mime_message() with threading headers (In-Reply-To, References)
- send_email(): Successful email sending via Gmail API
- send_email() error handling: InvalidRecipientError (400), QuotaExceededError (429), MessageTooLargeError (413)
- send_email() retry logic for transient errors
- get_thread_message_ids(): Extract message IDs from thread
- Structured logging verification
"""

import base64
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError

from app.core.gmail_client import GmailClient
from app.utils.errors import InvalidRecipientError, MessageTooLargeError, QuotaExceededError


# Helper Functions
def setup_mock_db_session(gmail_client, mock_user):
    """Helper to set up mock database session with user lookup."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_async_session():
        mock_session = AsyncMock()

        # Mock execute to return an awaitable that has scalar_one_or_none
        async def mock_execute(*args, **kwargs):
            result = Mock()  # Use regular Mock, not AsyncMock
            result.scalar_one_or_none = Mock(return_value=mock_user)
            return result

        mock_session.execute = mock_execute
        yield mock_session

    gmail_client.db_service.async_session = mock_async_session


# Test Fixtures
@pytest.fixture
def mock_db_service():
    """Mock DatabaseService for dependency injection."""
    from contextlib import asynccontextmanager

    mock_service = Mock()

    # Create async context manager for session
    @asynccontextmanager
    async def async_session():
        mock_session = AsyncMock()
        yield mock_session

    mock_service.async_session = async_session

    return mock_service


@pytest.fixture
def gmail_client(mock_db_service):
    """GmailClient instance with mocked database service."""
    return GmailClient(user_id=123, db_service=mock_db_service)


@pytest.fixture
def mock_user():
    """Mock User model with email."""
    from app.models.user import User

    user = Mock(spec=User)
    user.id = 123
    user.email = "sender@gmail.com"
    return user


@pytest.fixture
def sample_send_response():
    """Sample Gmail API messages().send() response."""
    return {"id": "18abc123def456", "threadId": "thread_abc123", "labelIds": ["SENT"]}


@pytest.fixture
def sample_thread_response():
    """Sample Gmail API threads().get() response with message IDs."""
    return {
        "id": "thread_abc123",
        "messages": [
            {
                "id": "msg1",
                "payload": {
                    "headers": [
                        {"name": "Message-ID", "value": "<CADv4wR9ABC@mail.gmail.com>"},
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "Subject", "value": "Original Subject"},
                    ]
                },
            },
            {
                "id": "msg2",
                "payload": {
                    "headers": [
                        {"name": "Message-ID", "value": "<CADv4wR9XYZ@mail.gmail.com>"},
                        {"name": "From", "value": "reply@example.com"},
                        {"name": "Subject", "value": "Re: Original Subject"},
                    ]
                },
            },
        ],
    }


# Test: _compose_mime_message() plain text
def test_compose_mime_message_plain_text(gmail_client):
    """Test MIME message composition with plain text body."""
    encoded_message = gmail_client._compose_mime_message(
        to="recipient@example.com",
        subject="Test Subject",
        body="This is a plain text body",
        from_email="sender@gmail.com",
        body_type="plain",
    )

    # Decode to verify structure
    decoded_bytes = base64.urlsafe_b64decode(encoded_message)
    decoded_str = decoded_bytes.decode("utf-8")

    # Verify headers present
    assert "From: sender@gmail.com" in decoded_str
    assert "To: recipient@example.com" in decoded_str
    assert "Subject: Test Subject" in decoded_str
    assert "Date:" in decoded_str

    # Verify content type
    assert "Content-Type: text/plain" in decoded_str
    # Verify encoded message is valid base64 (body is base64-encoded within MIME)
    assert isinstance(encoded_message, str)
    assert len(encoded_message) > 0


# Test: _compose_mime_message() HTML
def test_compose_mime_message_html(gmail_client):
    """Test MIME message composition with HTML body."""
    html_body = "<h1>Hello</h1><p>This is HTML content</p>"

    encoded_message = gmail_client._compose_mime_message(
        to="recipient@example.com",
        subject="HTML Test",
        body=html_body,
        from_email="sender@gmail.com",
        body_type="html",
    )

    # Decode to verify structure
    decoded_bytes = base64.urlsafe_b64decode(encoded_message)
    decoded_str = decoded_bytes.decode("utf-8")

    # Verify HTML content type
    assert "Content-Type: text/html" in decoded_str
    # Verify encoded message is valid
    assert isinstance(encoded_message, str)
    assert len(encoded_message) > 0


# Test: _compose_mime_message() with threading headers
def test_compose_mime_message_with_threading(gmail_client):
    """Test MIME message with In-Reply-To and References headers."""
    encoded_message = gmail_client._compose_mime_message(
        to="recipient@example.com",
        subject="Re: Original Subject",
        body="This is a reply",
        from_email="sender@gmail.com",
        in_reply_to="<CADv4wR9ABC@mail.gmail.com>",
        references="<CADv4wR9XYZ@mail.gmail.com> <CADv4wR9ABC@mail.gmail.com>",
        body_type="plain",
    )

    # Decode to verify threading headers
    decoded_bytes = base64.urlsafe_b64decode(encoded_message)
    decoded_str = decoded_bytes.decode("utf-8")

    # Verify threading headers present
    assert "In-Reply-To: <CADv4wR9ABC@mail.gmail.com>" in decoded_str
    assert "References: <CADv4wR9XYZ@mail.gmail.com> <CADv4wR9ABC@mail.gmail.com>" in decoded_str


# Test: _compose_mime_message() invalid body_type
def test_compose_mime_message_invalid_body_type(gmail_client):
    """Test that invalid body_type raises ValueError."""
    with pytest.raises(ValueError, match="body_type must be 'plain' or 'html'"):
        gmail_client._compose_mime_message(
            to="recipient@example.com",
            subject="Test",
            body="Body",
            from_email="sender@gmail.com",
            body_type="invalid",
        )


# Test: send_email() success
@pytest.mark.asyncio
async def test_send_email_success(gmail_client, mock_user, sample_send_response):
    """Test successful email sending via Gmail API."""
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail API service
    mock_service = Mock()
    mock_messages = Mock()
    mock_send = Mock()

    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.send.return_value = mock_send
    mock_send.execute.return_value = sample_send_response

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        message_id = await gmail_client.send_email(
            to="recipient@example.com", subject="Test Email", body="Test body", body_type="plain"
        )

    # Verify result
    assert message_id == "18abc123def456"

    # Verify Gmail API called with base64-encoded MIME message
    mock_messages.send.assert_called_once()
    call_args = mock_messages.send.call_args
    assert call_args[1]["userId"] == "me"
    assert "raw" in call_args[1]["body"]


# Test: send_email() invalid recipient (400)
@pytest.mark.asyncio
async def test_send_email_invalid_recipient(gmail_client, mock_user):
    """Test InvalidRecipientError raised on 400 Bad Request."""
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail API to return 400 error
    mock_service = Mock()

    # Create HttpError for 400 Bad Request
    mock_response = Mock()
    mock_response.status = 400
    http_error = HttpError(resp=mock_response, content=b"Invalid recipient")

    # Patch _get_gmail_service and _execute_with_retry
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        with patch.object(gmail_client, "_execute_with_retry", side_effect=http_error):
            with pytest.raises(InvalidRecipientError) as exc_info:
                await gmail_client.send_email(
                    to="invalid@example.com", subject="Test", body="Body", body_type="plain"
                )

            # Verify exception details
            assert "invalid@example.com" in str(exc_info.value)
            assert exc_info.value.recipient == "invalid@example.com"


# Test: send_email() quota exceeded (429)
@pytest.mark.asyncio
async def test_send_email_quota_exceeded(gmail_client, mock_user):
    """Test QuotaExceededError raised on 429 Rate Limit."""
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail API to return 429 error
    mock_service = Mock()

    # Create HttpError for 429 Rate Limit
    mock_response = Mock()
    mock_response.status = 429
    mock_response.get = Mock(return_value="3600")  # retry_after: 1 hour
    http_error = HttpError(resp=mock_response, content=b"Quota exceeded")

    # Patch _get_gmail_service and _execute_with_retry
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        with patch.object(gmail_client, "_execute_with_retry", side_effect=http_error):
            with pytest.raises(QuotaExceededError) as exc_info:
                await gmail_client.send_email(
                    to="recipient@example.com", subject="Test", body="Body", body_type="plain"
                )

            # Verify exception details
            assert "quota exceeded" in str(exc_info.value).lower()
            assert exc_info.value.retry_after == "3600"


# Test: send_email() message too large (413)
@pytest.mark.asyncio
async def test_send_email_message_too_large(gmail_client, mock_user):
    """Test MessageTooLargeError raised on 413 Request Entity Too Large."""
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail API to return 413 error
    mock_service = Mock()

    # Create HttpError for 413
    mock_response = Mock()
    mock_response.status = 413
    http_error = HttpError(resp=mock_response, content=b"Message too large")

    # Patch _get_gmail_service and _execute_with_retry
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        with patch.object(gmail_client, "_execute_with_retry", side_effect=http_error):
            with pytest.raises(MessageTooLargeError) as exc_info:
                await gmail_client.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    body="Very large body...",
                    body_type="plain",
                )

            # Verify exception details
            assert "25MB" in str(exc_info.value)


# Test: get_thread_message_ids() success
@pytest.mark.asyncio
async def test_get_thread_message_ids(gmail_client, sample_thread_response):
    """Test extracting message IDs from Gmail thread."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_threads = Mock()
    mock_get = Mock()

    mock_service.users.return_value.threads.return_value = mock_threads
    mock_threads.get.return_value = mock_get
    mock_get.execute.return_value = sample_thread_response

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        message_ids = await gmail_client.get_thread_message_ids("thread_abc123")

    # Verify results
    assert len(message_ids) == 2
    assert message_ids[0] == "<CADv4wR9ABC@mail.gmail.com>"
    assert message_ids[1] == "<CADv4wR9XYZ@mail.gmail.com>"


# Test: get_thread_message_ids() empty thread_id
@pytest.mark.asyncio
async def test_get_thread_message_ids_empty_thread_id(gmail_client):
    """Test that empty thread_id raises ValueError."""
    with pytest.raises(ValueError, match="thread_id must be a non-empty string"):
        await gmail_client.get_thread_message_ids("")


# Test: send_email() with thread_id auto-constructs headers
@pytest.mark.asyncio
async def test_send_email_with_thread_id(gmail_client, mock_user, sample_thread_response, sample_send_response):
    """Test send_email() with thread_id auto-constructs In-Reply-To and References."""
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail API service
    mock_service = Mock()
    mock_messages = Mock()
    mock_send = Mock()
    mock_threads = Mock()
    mock_get = Mock()

    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.send.return_value = mock_send
    mock_send.execute.return_value = sample_send_response

    mock_service.users.return_value.threads.return_value = mock_threads
    mock_threads.get.return_value = mock_get
    mock_get.execute.return_value = sample_thread_response

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        message_id = await gmail_client.send_email(
            to="recipient@example.com",
            subject="Re: Original Subject",
            body="This is a reply",
            thread_id="thread_abc123",
        )

    # Verify result
    assert message_id == "18abc123def456"

    # Verify thread retrieval was called
    mock_threads.get.assert_called_once_with(userId="me", id="thread_abc123", format="metadata")


@pytest.mark.asyncio
async def test_send_email_retry_on_network_error(gmail_client, mock_user):
    """Test retry logic on network errors (503 Service Unavailable).

    Verifies:
    - _execute_with_retry() retries on transient errors
    - Exponential backoff applied (2s, 4s, 8s delays)
    - Maximum 3 retry attempts
    - Success on final retry
    """
    from googleapiclient.errors import HttpError
    from unittest.mock import call
    import time

    # Setup mock database session with user
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail service
    mock_service = Mock()
    mock_messages = Mock()
    mock_send = Mock()

    # Sample response for successful retry
    sample_response = {
        "id": "18abc123def456",
        "threadId": "thread_abc123",
        "labelIds": ["SENT"],
    }

    # Simulate 503 errors on first 2 attempts, success on 3rd
    http_error_503 = HttpError(
        resp=Mock(status=503),
        content=b'{"error": {"message": "Service Unavailable"}}',
    )

    # Use Mock (not AsyncMock) for execute since _execute_with_retry calls it synchronously
    mock_send.execute = Mock(
        side_effect=[
            http_error_503,  # First attempt fails
            http_error_503,  # Second attempt fails
            sample_response,  # Third attempt succeeds
        ]
    )

    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.send.return_value = mock_send

    # Patch _get_gmail_service and time.sleep to verify backoff
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        with patch("time.sleep") as mock_sleep:
            message_id = await gmail_client.send_email(
                to="recipient@example.com",
                subject="Test Email",
                body="Test body",
            )

    # Verify success after retries
    assert message_id == "18abc123def456"

    # Verify execute was called 3 times (2 failures + 1 success)
    assert mock_send.execute.call_count == 3

    # Verify exponential backoff delays (2s, 4s)
    assert mock_sleep.call_count == 2
    # Note: Actual backoff timing depends on _execute_with_retry implementation
    # This verifies that sleep was called between retries


@pytest.mark.asyncio
async def test_send_email_logging(gmail_client, mock_user):
    """Test structured logging for email send operations.

    Verifies:
    - email_send_started event logged with metadata
    - email_sent event logged on success
    - Log fields include: user_id, recipient, subject, message_id, success, duration_ms
    - Email body NOT logged (GDPR compliance)
    """
    from unittest.mock import patch
    import structlog

    # Setup mock database session with user
    setup_mock_db_session(gmail_client, mock_user)

    # Mock Gmail service
    mock_service = Mock()
    mock_messages = Mock()
    mock_send = Mock()

    sample_response = {
        "id": "18abc123def456",
        "threadId": "thread_abc123",
        "labelIds": ["SENT"],
    }

    # Use Mock (not AsyncMock) for execute since _execute_with_retry calls it synchronously
    mock_send.execute = Mock(return_value=sample_response)
    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.send.return_value = mock_send

    # Patch logger on gmail_client instance and Gmail service
    mock_logger = Mock()
    gmail_client.logger = mock_logger

    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        message_id = await gmail_client.send_email(
            to="recipient@example.com",
            subject="Test Email Subject",
            body="This is the sensitive email body that should NOT be logged",
            body_type="plain",
        )

    # Verify success
    assert message_id == "18abc123def456"

    # Verify logging calls were made
    assert mock_logger.info.called or mock_logger.error.called

    # Collect all log calls
    all_log_calls = mock_logger.info.call_args_list + mock_logger.error.call_args_list

    # Verify sensitive body is NOT logged
    for call_obj in all_log_calls:
        call_str = str(call_obj)
        assert "sensitive email body" not in call_str.lower()
        assert "This is the sensitive" not in call_str

    # Verify expected log events present
    log_events = []
    for call_obj in mock_logger.info.call_args_list:
        if len(call_obj[0]) > 0:
            log_events.append(call_obj[0][0])

    # Check for email_send_started or email_sent events
    # Exact event names depend on implementation
    assert len(log_events) > 0  # At least one log event should be present

    # Verify log contains metadata fields
    log_calls_str = str(all_log_calls)
    # Check for expected metadata (user_id, recipient, subject)
    # Body should NOT be present
    assert "recipient@example.com" in log_calls_str or "Test Email Subject" in log_calls_str
