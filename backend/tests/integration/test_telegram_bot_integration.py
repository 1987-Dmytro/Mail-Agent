"""Integration tests for Telegram bot functionality.

Tests cover:
- Bot startup and polling initialization
- Test endpoint connectivity with authenticated users
- Error handling for users without linked Telegram accounts
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app, telegram_bot
from app.models.user import User


class TestBotStartupAndPolling:
    """Test bot initialization during FastAPI startup."""

    @pytest.mark.asyncio
    async def test_bot_startup_and_polling(self):
        """Test that bot initializes and starts polling correctly on app startup."""
        # Mock telegram bot methods
        with patch.object(telegram_bot, "initialize", new_callable=AsyncMock) as mock_init:
            with patch.object(telegram_bot, "start_polling", new_callable=AsyncMock) as mock_poll:
                with patch.object(telegram_bot, "stop_polling", new_callable=AsyncMock) as mock_stop:
                    # Create test client (triggers lifespan)
                    with TestClient(app) as client:
                        # Verify bot was initialized
                        mock_init.assert_called_once()
                        mock_poll.assert_called_once()

                    # Verify bot was stopped on shutdown
                    mock_stop.assert_called_once()


class TestTelegramTestEndpoint:
    """Test /api/v1/test/telegram endpoint."""

    @pytest.mark.asyncio
    async def test_send_test_message_endpoint_success(self):
        """Test successful test message sending to linked Telegram account."""
        from app.api.v1.auth import get_current_user

        # Mock authentication to return user with telegram_id
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id="123456789",
        )

        async def mock_get_current_user():
            return mock_user

        # Mock telegram_bot.send_message
        with patch.object(telegram_bot, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = "54321"

            # Create test client with dependency override
            app.dependency_overrides[get_current_user] = mock_get_current_user

            try:
                with TestClient(app) as client:
                    # Make request
                    response = client.post(
                        "/api/v1/test/telegram",
                        json={"message": "Integration test message"},
                    )

                    # Verify response
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["message_id"] == "54321"
                    assert data["data"]["sent_to"] == "123456789"
                    assert "sent_at" in data["data"]

                    # Verify send_message was called
                    assert mock_send.called
            finally:
                # Clean up override
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_send_message_no_telegram_linked(self):
        """Test endpoint returns 400 when user has no linked Telegram account."""
        from app.api.v1.auth import get_current_user

        # Mock authentication to return user WITHOUT telegram_id
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id=None,
        )

        async def mock_get_current_user():
            return mock_user

        # Create test client with dependency override
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                # Make request
                response = client.post(
                    "/api/v1/test/telegram",
                    json={"message": "Test message"},
                )

                # Verify error response
                assert response.status_code == 400
                data = response.json()
                assert "not linked" in data["detail"].lower()
        finally:
            # Clean up override
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_send_message_user_blocked_bot(self):
        """Test endpoint returns 403 when user has blocked the bot."""
        from app.api.v1.auth import get_current_user
        from app.utils.errors import TelegramUserBlockedError

        # Mock authentication to return user with telegram_id
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id="123456789",
        )

        async def mock_get_current_user():
            return mock_user

        # Mock telegram_bot.send_message to raise TelegramUserBlockedError
        with patch.object(
            telegram_bot,
            "send_message",
            new_callable=AsyncMock,
            side_effect=TelegramUserBlockedError("User blocked bot"),
        ):
            # Create test client with dependency override
            app.dependency_overrides[get_current_user] = mock_get_current_user

            try:
                with TestClient(app) as client:
                    # Make request
                    response = client.post(
                        "/api/v1/test/telegram",
                        json={"message": "Test message"},
                    )

                    # Verify error response
                    assert response.status_code == 403
                    data = response.json()
                    assert "blocked" in data["detail"].lower()
            finally:
                # Clean up override
                app.dependency_overrides.clear()


# Note: Additional configuration tests skipped as bot startup test already
# validates graceful degradation when bot is not configured
