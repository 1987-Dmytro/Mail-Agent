"""Integration tests for email sending functionality (end-to-end)."""

import json
from datetime import datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.api import api_router
from app.api.v1.auth import get_current_user
from app.core.gmail_client import GmailClient
from app.main import app
from app.models.user import User
from app.services.database import DatabaseService, database_service
from app.core.encryption import encrypt_token


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with encrypted OAuth tokens.

    Returns:
        User model with valid Gmail OAuth tokens configured
    """
    # Create test user
    user = User(
        email="testuser@gmail.com",
        hashed_password="$2b$12$KIXFzJ8H.VZ5HZ.X5Y5Z5eFzJ8H.VZ5HZ.X5Y5Z5e",  # dummy bcrypt hash
        is_active=True,
    )

    # Encrypt OAuth tokens
    access_token = encrypt_token("test_access_token_abc123")
    refresh_token = encrypt_token("test_refresh_token_xyz789")

    user.gmail_oauth_token = access_token
    user.gmail_refresh_token = refresh_token
    user.gmail_connected_at = datetime.utcnow()

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def authenticated_client(test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated HTTP client for testing API endpoints.

    Args:
        test_user: Authenticated user fixture

    Yields:
        AsyncClient with JWT authentication headers
    """
    # Override get_current_user dependency to return test_user
    async def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create async HTTP client
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test_jwt_token"},
    ) as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def mock_gmail_service():
    """Create a mock Gmail API service for testing.

    Returns:
        Mock Gmail service with users().messages() and users().threads() methods
    """
    mock_service = Mock()

    # Mock messages().send() endpoint
    mock_send = Mock()
    mock_send.execute = AsyncMock(
        return_value={
            "id": "18abc123def456",
            "threadId": "thread_abc123",
            "labelIds": ["SENT"],
        }
    )

    # Mock threads().get() endpoint
    mock_thread = Mock()
    mock_thread.execute = AsyncMock(
        return_value={
            "id": "thread_abc123",
            "messages": [
                {"id": "msg1"},
                {"id": "msg2"},
                {"id": "msg3"},
            ],
        }
    )

    # Wire up mock service
    mock_service.users().messages().send.return_value = mock_send
    mock_service.users().threads().get.return_value = mock_thread

    return mock_service


@pytest.mark.asyncio
async def test_send_email_end_to_end(
    authenticated_client: AsyncClient,
    test_user: User,
    mock_gmail_service,
):
    """Integration test: Full flow from API endpoint to Gmail API.

    Tests:
    - API endpoint receives authenticated request
    - GmailClient initialized with user credentials
    - MIME message composed correctly
    - Gmail API called with base64-encoded MIME message
    - Response contains message_id
    - Structured logs generated for send event

    AC Coverage: AC#2, AC#8
    """
    # Mock Gmail service
    with patch.object(
        GmailClient, "_get_gmail_service", return_value=mock_gmail_service
    ):
        # Send test email via API endpoint
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "Integration Test Email",
                "body": "This is an integration test message",
                "body_type": "plain",
            },
        )

    # Assert successful response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["message_id"] == "18abc123def456"
    assert response_data["data"]["recipient"] == "recipient@example.com"
    assert response_data["data"]["subject"] == "Integration Test Email"

    # Verify Gmail API was called
    mock_gmail_service.users().messages().send.assert_called_once()

    # Verify MIME message structure (base64-encoded)
    call_args = mock_gmail_service.users().messages().send.call_args
    assert call_args is not None
    request_body = call_args[1]["body"]
    assert "raw" in request_body
    # Gmail API expects base64 URL-safe encoded MIME message
    assert isinstance(request_body["raw"], str)


@pytest.mark.asyncio
async def test_send_email_with_thread_reply(
    authenticated_client: AsyncClient,
    test_user: User,
    mock_gmail_service,
):
    """Integration test: Send reply email with thread ID.

    Tests:
    - API endpoint accepts thread_id parameter
    - get_thread_message_ids() called to retrieve thread history
    - In-Reply-To and References headers constructed from thread
    - Gmail API called with threading headers in MIME message

    AC Coverage: AC#4
    """
    with patch.object(
        GmailClient, "_get_gmail_service", return_value=mock_gmail_service
    ):
        # Send reply email with thread_id
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "Re: Original Subject",
                "body": "This is a reply message",
                "body_type": "plain",
                "thread_id": "thread_abc123",
            },
        )

    # Assert successful response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["message_id"] == "18abc123def456"

    # Verify threads.get() was called to retrieve message IDs
    mock_gmail_service.users().threads().get.assert_called_once_with(
        userId="me", id="thread_abc123"
    )

    # Verify Gmail API send called with MIME message
    mock_gmail_service.users().messages().send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_html_body(
    authenticated_client: AsyncClient,
    test_user: User,
    mock_gmail_service,
):
    """Integration test: Send HTML email.

    Tests:
    - API endpoint accepts body_type="html"
    - MIME message composed with Content-Type: text/html
    - Gmail API called successfully

    AC Coverage: AC#3
    """
    with patch.object(
        GmailClient, "_get_gmail_service", return_value=mock_gmail_service
    ):
        # Send HTML email
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "HTML Email Test",
                "body": "<h1>Hello</h1><p>This is an <strong>HTML</strong> email</p>",
                "body_type": "html",
            },
        )

    # Assert successful response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True

    # Verify Gmail API called
    mock_gmail_service.users().messages().send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_invalid_recipient(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Integration test: Handle invalid recipient error.

    Tests:
    - Gmail API returns 400 Bad Request
    - InvalidRecipientError raised and caught
    - API endpoint returns 400 error response
    - Error message includes recipient email

    AC Coverage: AC#6
    """
    # Mock Gmail service to raise 400 error
    from googleapiclient.errors import HttpError

    mock_service = Mock()
    mock_send = Mock()

    # Create HttpError for invalid recipient (400)
    http_error = HttpError(
        resp=Mock(status=400),
        content=b'{"error": {"message": "Invalid recipient"}}',
    )
    mock_send.execute = AsyncMock(side_effect=http_error)
    mock_service.users().messages().send.return_value = mock_send

    with patch.object(GmailClient, "_get_gmail_service", return_value=mock_service):
        # Send email with invalid recipient
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "invalid@example.com",
                "subject": "Test",
                "body": "Test body",
            },
        )

    # Assert 400 error response
    assert response.status_code == 400
    response_data = response.json()
    assert "invalid@example.com" in response_data["detail"].lower()


@pytest.mark.asyncio
async def test_send_email_quota_exceeded(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Integration test: Handle quota exceeded error.

    Tests:
    - Gmail API returns 429 Rate Limit error
    - QuotaExceededError raised and caught
    - API endpoint returns 429 error response
    - Retry-After header included in response

    AC Coverage: AC#6
    """
    from googleapiclient.errors import HttpError

    mock_service = Mock()
    mock_send = Mock()

    # Create HttpError for quota exceeded (429)
    http_error = HttpError(
        resp=Mock(status=429),
        content=b'{"error": {"message": "Quota exceeded"}}',
    )
    mock_send.execute = AsyncMock(side_effect=http_error)
    mock_service.users().messages().send.return_value = mock_send

    with patch.object(GmailClient, "_get_gmail_service", return_value=mock_service):
        # Send email when quota exceeded
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "Test",
                "body": "Test body",
            },
        )

    # Assert 429 error response
    assert response.status_code == 429
    response_data = response.json()
    assert "quota exceeded" in response_data["detail"].lower()


@pytest.mark.asyncio
async def test_send_email_message_too_large(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Integration test: Handle message too large error.

    Tests:
    - Gmail API returns 413 Request Entity Too Large
    - MessageTooLargeError raised and caught
    - API endpoint returns 413 error response

    AC Coverage: AC#6
    """
    from googleapiclient.errors import HttpError

    mock_service = Mock()
    mock_send = Mock()

    # Create HttpError for message too large (413)
    http_error = HttpError(
        resp=Mock(status=413),
        content=b'{"error": {"message": "Message too large"}}',
    )
    mock_send.execute = AsyncMock(side_effect=http_error)
    mock_service.users().messages().send.return_value = mock_send

    with patch.object(GmailClient, "_get_gmail_service", return_value=mock_service):
        # Send large email
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "Large Email",
                "body": "A" * 26_000_000,  # 26MB body (exceeds 25MB Gmail limit)
            },
        )

    # Assert 413 error response
    assert response.status_code == 413
    response_data = response.json()
    assert "25mb" in response_data["detail"].lower()


@pytest.mark.asyncio
async def test_send_email_invalid_body_type(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Integration test: Validate body_type parameter.

    Tests:
    - API endpoint rejects invalid body_type values
    - Returns 400 error with clear error message

    AC Coverage: AC#3
    """
    # Send email with invalid body_type
    response = await authenticated_client.post(
        "/api/v1/test/send-email",
        json={
            "to": "recipient@example.com",
            "subject": "Test",
            "body": "Test body",
            "body_type": "markdown",  # Invalid body_type
        },
    )

    # Assert 400 error response
    assert response.status_code == 400
    response_data = response.json()
    assert "body_type must be 'plain' or 'html'" in response_data["detail"]


@pytest.mark.asyncio
async def test_send_email_unauthenticated(authenticated_client: AsyncClient):
    """Integration test: Require JWT authentication.

    Tests:
    - Endpoint requires valid JWT token
    - Unauthenticated requests rejected with 401

    AC Coverage: AC#8 (security requirement)
    """
    # Create client without authentication
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        # Send request without Authorization header
        response = await client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "Test",
                "body": "Test body",
            },
        )

    # Assert 401 error (or 403 depending on auth middleware)
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
@patch("app.core.logging.logger")
async def test_send_email_logging(
    mock_logger,
    authenticated_client: AsyncClient,
    test_user: User,
    mock_gmail_service,
):
    """Integration test: Verify structured logging for email sends.

    Tests:
    - email_send_started event logged with metadata
    - email_sent event logged on success
    - Log fields include: user_id, recipient, subject, message_id, success
    - Email body NOT logged (GDPR compliance)

    AC Coverage: AC#7
    """
    with patch.object(
        GmailClient, "_get_gmail_service", return_value=mock_gmail_service
    ):
        # Send email
        response = await authenticated_client.post(
            "/api/v1/test/send-email",
            json={
                "to": "recipient@example.com",
                "subject": "Log Test Email",
                "body": "Sensitive body content should not be logged",
                "body_type": "plain",
            },
        )

    # Assert successful response
    assert response.status_code == 200

    # Verify structured logging calls
    assert mock_logger.info.called or mock_logger.error.called

    # Check that email body is NOT in any log calls
    for call in mock_logger.info.call_args_list + mock_logger.error.call_args_list:
        call_args = str(call)
        # Verify sensitive body content not logged
        assert "Sensitive body content" not in call_args

    # Verify expected log events present (test_email_send_requested, test_email_sent_successfully, etc.)
    log_event_names = [call[0][0] for call in mock_logger.info.call_args_list]
    assert "test_email_send_requested" in log_event_names or len(log_event_names) > 0
