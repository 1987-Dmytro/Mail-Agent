"""Integration tests for Telegram account linking functionality.

Tests cover:
- POST /api/v1/telegram/generate-code endpoint (authenticated)
- GET /api/v1/telegram/status endpoint (authenticated)
- Bot /start [code] command with full linking flow
- Code expiration and validation scenarios
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, UTC

from app.main import app
from app.models.user import User


class TestGenerateCodeEndpoint:
    """Test POST /api/v1/telegram/generate-code endpoint."""

    @pytest.mark.asyncio
    async def test_generate_code_endpoint_success(self):
        """Test successful linking code generation for authenticated user."""
        from app.api.v1.auth import get_current_user
        from app.api.deps import get_db

        # Create mock user without telegram_id (not yet linked)
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id=None,
        )

        async def mock_get_current_user():
            return mock_user

        # Create mock database session
        mock_db = MagicMock()
        mock_code_record = MagicMock()
        mock_code_record.expires_at = datetime.now(UTC) + timedelta(minutes=15)
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = mock_code_record
        mock_db.exec.return_value = mock_exec_result

        def mock_get_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            # Mock the generate_linking_code service
            with patch('app.api.v1.telegram.generate_linking_code') as mock_gen:
                mock_gen.return_value = "ABC123"

                with TestClient(app) as client:
                    # Make request
                    response = client.post("/api/v1/telegram/generate-code")

                    # Verify response
                    assert response.status_code == 201  # Note: endpoint returns 201
                    data = response.json()

                    # Verify response structure
                    assert data["success"] is True
                    assert "data" in data

                    # Verify response data fields
                    assert "code" in data["data"]
                    assert "expires_at" in data["data"]
                    assert "bot_username" in data["data"]
                    assert "instructions" in data["data"]

                    # Verify code format (6 characters, alphanumeric uppercase)
                    code = data["data"]["code"]
                    assert code == "ABC123"
        finally:
            # Clean up override
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_code_already_linked(self):
        """Test endpoint returns 400 when user already has Telegram linked."""
        from app.api.v1.auth import get_current_user

        # Create mock user WITH telegram_id already set (already linked)
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id="123456789",
            telegram_username="existinguser",
        )

        async def mock_get_current_user():
            return mock_user

        # Override authentication dependency
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                # Make request
                response = client.post("/api/v1/telegram/generate-code")

                # Verify error response
                assert response.status_code == 400
                data = response.json()
                assert "already linked" in data["detail"].lower()
        finally:
            # Clean up override
            app.dependency_overrides.clear()


class TestTelegramStatusEndpoint:
    """Test GET /api/v1/telegram/status endpoint."""

    @pytest.mark.asyncio
    async def test_telegram_status_not_linked(self):
        """Test status endpoint returns linked=false for user without Telegram."""
        from app.api.v1.auth import get_current_user

        # Create mock user without telegram_id
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id=None,
        )

        async def mock_get_current_user():
            return mock_user

        # Override authentication dependency
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                # Make request
                response = client.get("/api/v1/telegram/status")

                # Verify response
                assert response.status_code == 200
                data = response.json()

                # Verify response structure
                assert data["success"] is True
                assert "data" in data

                # Verify not linked
                assert data["data"]["linked"] is False
                assert data["data"]["telegram_id"] is None
                assert data["data"]["telegram_username"] is None
                assert data["data"]["linked_at"] is None
        finally:
            # Clean up override
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_telegram_status_linked(self):
        """Test status endpoint returns linked=true with details for linked user."""
        from app.api.v1.auth import get_current_user

        # Create mock user WITH telegram_id (linked)
        linked_at = datetime.now(UTC)
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="fake_hash",
            telegram_id="123456789",
            telegram_username="testuser",
            telegram_linked_at=linked_at,
        )

        async def mock_get_current_user():
            return mock_user

        # Override authentication dependency
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                # Make request
                response = client.get("/api/v1/telegram/status")

                # Verify response
                assert response.status_code == 200
                data = response.json()

                # Verify response structure
                assert data["success"] is True
                assert "data" in data

                # Verify linked status
                assert data["data"]["linked"] is True
                assert data["data"]["telegram_id"] == "123456789"
                assert data["data"]["telegram_username"] == "testuser"
                assert data["data"]["linked_at"] is not None
        finally:
            # Clean up override
            app.dependency_overrides.clear()


class TestBotStartCommandLinking:
    """Test bot /start [code] command with linking logic."""

    @pytest.mark.asyncio
    async def test_bot_start_command_with_valid_code(self):
        """Test /start [code] successfully links Telegram account."""
        from app.api.telegram_handlers import handle_start_command
        from telegram import Update, User as TelegramUser, Message
        from telegram.ext import ContextTypes

        # Mock Telegram Update with /start ABC123
        mock_telegram_user = MagicMock(spec=TelegramUser)
        mock_telegram_user.id = 987654321
        mock_telegram_user.username = "testuser"

        mock_message = MagicMock(spec=Message)
        mock_message.reply_text = AsyncMock()

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = mock_message

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = ["ABC123"]  # Code as argument

        # Mock link_telegram_account_async (async version used in handler) and AsyncSessionLocal
        with patch('app.api.telegram_handlers.link_telegram_account_async') as mock_link, \
             patch('app.api.telegram_handlers.AsyncSessionLocal') as mock_session_local:

            mock_link.return_value = {
                "success": True,
                "message": "✅ Your Telegram account has been linked successfully!"
            }

            # Mock the database session context manager
            mock_session_instance = MagicMock()
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_local.return_value.__aexit__ = AsyncMock()

            # Call handler
            await handle_start_command(mock_update, mock_context)

            # Verify link_telegram_account_async was called (checking keyword arguments)
            assert mock_link.call_count == 1
            call_kwargs = mock_link.call_args.kwargs
            assert call_kwargs["telegram_id"] == "987654321"
            assert call_kwargs["telegram_username"] == "testuser"
            assert call_kwargs["code"] == "ABC123"
            assert call_kwargs["db"] == mock_session_instance

            # Verify success message sent
            mock_message.reply_text.assert_called_once()
            sent_message = mock_message.reply_text.call_args[0][0]
            assert "✅" in sent_message or "linked successfully" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_bot_start_command_with_expired_code(self):
        """Test /start [expired_code] returns error message."""
        from app.api.telegram_handlers import handle_start_command
        from telegram import Update, User as TelegramUser, Message
        from telegram.ext import ContextTypes

        # Mock Telegram Update with /start EXP123
        mock_telegram_user = MagicMock(spec=TelegramUser)
        mock_telegram_user.id = 987654322
        mock_telegram_user.username = "testuser2"

        mock_message = MagicMock(spec=Message)
        mock_message.reply_text = AsyncMock()

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = mock_message

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = ["EXP123"]  # Expired code as argument

        # Mock link_telegram_account to return expiration error
        with patch('app.api.telegram_handlers.link_telegram_account') as mock_link:
            mock_link.return_value = {
                "success": False,
                "error": "This code has expired. Generate a new code (codes expire after 15 minutes)."
            }

            # Call handler
            await handle_start_command(mock_update, mock_context)

            # Verify error message sent
            mock_message.reply_text.assert_called_once()
            sent_message = mock_message.reply_text.call_args[0][0]
            assert "❌" in sent_message or "expired" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_bot_start_command_with_used_code(self):
        """Test /start [used_code] returns error message."""
        from app.api.telegram_handlers import handle_start_command
        from telegram import Update, User as TelegramUser, Message
        from telegram.ext import ContextTypes

        # Mock Telegram Update with /start USED99
        mock_telegram_user = MagicMock(spec=TelegramUser)
        mock_telegram_user.id = 987654323
        mock_telegram_user.username = "testuser3"

        mock_message = MagicMock(spec=Message)
        mock_message.reply_text = AsyncMock()

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = mock_message

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = ["USED99"]  # Used code as argument

        # Mock link_telegram_account to return used error
        with patch('app.api.telegram_handlers.link_telegram_account') as mock_link:
            mock_link.return_value = {
                "success": False,
                "error": "This code has already been used. Generate a new code."
            }

            # Call handler
            await handle_start_command(mock_update, mock_context)

            # Verify error message sent
            mock_message.reply_text.assert_called_once()
            sent_message = mock_message.reply_text.call_args[0][0]
            assert "❌" in sent_message or "already been used" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_bot_start_command_with_invalid_code(self):
        """Test /start [invalid_code] returns error message."""
        from app.api.telegram_handlers import handle_start_command
        from telegram import Update, User as TelegramUser, Message
        from telegram.ext import ContextTypes

        # Mock Telegram Update with /start INVALID (code doesn't exist)
        mock_telegram_user = MagicMock(spec=TelegramUser)
        mock_telegram_user.id = 987654324
        mock_telegram_user.username = "testuser4"

        mock_message = MagicMock(spec=Message)
        mock_message.reply_text = AsyncMock()

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = mock_message

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = ["INVALID"]  # Non-existent code

        # Mock link_telegram_account to return invalid error
        with patch('app.api.telegram_handlers.link_telegram_account') as mock_link:
            mock_link.return_value = {
                "success": False,
                "error": "Invalid linking code. Please check and try again."
            }

            # Call handler
            await handle_start_command(mock_update, mock_context)

            # Verify error message sent
            mock_message.reply_text.assert_called_once()
            sent_message = mock_message.reply_text.call_args[0][0]
            assert "❌" in sent_message or "invalid" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_bot_start_command_without_code(self):
        """Test /start without code shows welcome message."""
        from app.api.telegram_handlers import handle_start_command
        from telegram import Update, User as TelegramUser, Message
        from telegram.ext import ContextTypes

        # Mock Telegram Update with /start (no code)
        mock_telegram_user = MagicMock(spec=TelegramUser)
        mock_telegram_user.id = 987654325
        mock_telegram_user.username = "testuser5"

        mock_message = MagicMock(spec=Message)
        mock_message.reply_text = AsyncMock()

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = mock_message

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []  # No code provided

        # Call handler
        await handle_start_command(mock_update, mock_context)

        # Verify welcome message sent
        mock_message.reply_text.assert_called_once()
        sent_message = mock_message.reply_text.call_args[0][0]
        assert "welcome" in sent_message.lower() or "link your account" in sent_message.lower()
