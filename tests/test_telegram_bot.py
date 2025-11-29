"""Unit tests for Telegram bot functionality.

Tests cover:
- TelegramBotClient initialization
- Message sending (success and error cases)
- Command handlers (/start, /help, /test)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import Forbidden, NetworkError

from app.core.telegram_bot import TelegramBotClient
from app.utils.errors import TelegramBotError, TelegramSendError, TelegramUserBlockedError


class TestTelegramBotInitialization:
    """Test Telegram bot initialization."""

    @pytest.mark.asyncio
    async def test_telegram_bot_initialization(self):
        """Test that TelegramBotClient initializes correctly with valid token."""
        # Mock Application builder
        with patch("app.core.telegram_bot.Application") as mock_application:
            mock_builder = MagicMock()
            mock_application.builder.return_value = mock_builder
            mock_builder.token.return_value = mock_builder
            mock_app = MagicMock()
            mock_builder.build.return_value = mock_app
            mock_bot = MagicMock()
            mock_bot.username = "TestBot"
            mock_app.bot = mock_bot
            mock_app.initialize = AsyncMock()
            mock_app.add_handler = MagicMock()

            # Mock settings
            with patch("app.core.telegram_bot.settings") as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

                # Create and initialize bot client
                bot_client = TelegramBotClient()
                await bot_client.initialize()

                # Verify application was built correctly
                mock_application.builder.assert_called_once()
                mock_builder.token.assert_called_once_with("test_token")
                mock_builder.build.assert_called_once()

                # Verify initialization completed
                assert bot_client.application is not None
                assert bot_client.bot is not None
                mock_app.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_telegram_bot_initialization_no_token(self):
        """Test that initialization fails gracefully when token is missing."""
        with patch("app.core.telegram_bot.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = ""

            bot_client = TelegramBotClient()

            with pytest.raises(TelegramBotError, match="TELEGRAM_BOT_TOKEN not configured"):
                await bot_client.initialize()


class TestSendMessage:
    """Test message sending functionality."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        # Create bot client and mock bot
        bot_client = TelegramBotClient()
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 12345
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        bot_client.bot = mock_bot

        # Send message
        message_id = await bot_client.send_message(
            telegram_id="123456789",
            text="Test message",
        )

        # Verify message was sent correctly
        mock_bot.send_message.assert_called_once_with(
            chat_id="123456789",
            text="Test message",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        # Verify message_id returned
        assert message_id == "12345"

    @pytest.mark.asyncio
    async def test_send_message_user_blocked(self):
        """Test that user blocked error is handled correctly."""
        # Create bot client and mock bot
        bot_client = TelegramBotClient()
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Forbidden("User blocked bot"))
        bot_client.bot = mock_bot

        # Attempt to send message
        with pytest.raises(TelegramUserBlockedError, match="User 123456789 has blocked the bot"):
            await bot_client.send_message(
                telegram_id="123456789",
                text="Test message",
            )

    @pytest.mark.asyncio
    async def test_send_message_network_error(self):
        """Test that network errors are handled correctly."""
        # Create bot client and mock bot
        bot_client = TelegramBotClient()
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=NetworkError("Connection timeout"))
        bot_client.bot = mock_bot

        # Attempt to send message
        with pytest.raises(TelegramSendError, match="Failed to send message.*after retries"):
            await bot_client.send_message(
                telegram_id="123456789",
                text="Test message",
            )

    @pytest.mark.asyncio
    async def test_send_message_not_initialized(self):
        """Test that sending message fails when bot not initialized."""
        bot_client = TelegramBotClient()

        with pytest.raises(TelegramBotError, match="Bot not initialized"):
            await bot_client.send_message(
                telegram_id="123456789",
                text="Test message",
            )

    @pytest.mark.asyncio
    async def test_send_message_invalid_telegram_id(self):
        """Test that invalid telegram_id format is rejected."""
        # Create bot client and mock bot
        bot_client = TelegramBotClient()
        mock_bot = MagicMock()
        bot_client.bot = mock_bot

        # Attempt to send message with invalid telegram_id (contains non-digits)
        with pytest.raises(ValueError, match="Invalid telegram_id format"):
            await bot_client.send_message(
                telegram_id="abc123",
                text="Test message",
            )

        # Verify send_message was never called
        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_exceeds_length_limit(self):
        """Test that messages exceeding 4096 characters are auto-truncated."""
        # Create bot client and mock bot
        bot_client = TelegramBotClient()
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 12345
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        bot_client.bot = mock_bot

        # Create a message longer than 4096 characters
        long_message = "a" * 4097

        # Send message - should truncate automatically
        message_id = await bot_client.send_message(
            telegram_id="123456789",
            text=long_message,
        )

        # Verify message was sent with truncated text (4000 chars + "...")
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        sent_text = call_args.kwargs["text"]
        assert len(sent_text) == 4003  # 4000 + "..."
        assert sent_text.endswith("...")
        assert message_id == "12345"


class TestSendMessageWithButtons:
    """Test message with buttons functionality."""

    @pytest.mark.asyncio
    async def test_send_message_with_buttons_success(self):
        """Test successful message with buttons sending."""
        from telegram import InlineKeyboardButton

        # Create bot client and mock bot
        bot_client = TelegramBotClient()
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 54321
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        bot_client.bot = mock_bot

        # Create buttons
        buttons = [
            [InlineKeyboardButton("Approve", callback_data="approve_123")],
            [InlineKeyboardButton("Reject", callback_data="reject_123")],
        ]

        # Send message with buttons
        message_id = await bot_client.send_message_with_buttons(
            telegram_id="123456789",
            text="Choose an option:",
            buttons=buttons,
        )

        # Verify message was sent
        assert mock_bot.send_message.called
        assert message_id == "54321"


class TestCommandHandlers:
    """Test bot command handlers."""

    @pytest.mark.asyncio
    async def test_start_command_handler(self):
        """Test /start command sends welcome message."""
        from app.api.telegram_handlers import handle_start_command

        # Mock Update and Context
        mock_update = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.effective_user.username = "testuser"
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.args = []

        # Call handler
        await handle_start_command(mock_update, mock_context)

        # Verify welcome message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Welcome to" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_start_command_handler_with_code(self):
        """Test /start command with linking code."""
        from app.api.telegram_handlers import handle_start_command

        # Mock the link_telegram_account_async function
        with patch("app.api.telegram_handlers.link_telegram_account_async") as mock_link, \
             patch("app.api.telegram_handlers.AsyncSessionLocal") as mock_session_local:

            # Mock successful linking response
            mock_link.return_value = {
                "success": True,
                "message": "✅ Your Telegram account has been linked successfully!"
            }

            # Mock the database session context manager
            mock_session_instance = MagicMock()
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_local.return_value.__aexit__ = AsyncMock()

            # Mock Update and Context with linking code
            mock_update = MagicMock()
            mock_update.effective_user.id = 123456789
            mock_update.effective_user.username = "testuser"
            mock_update.message.reply_text = AsyncMock()
            mock_context = MagicMock()
            mock_context.args = ["A3B7X9"]

            # Call handler
            await handle_start_command(mock_update, mock_context)

            # Verify linking function was called
            mock_link.assert_called_once_with(
                telegram_id="123456789",
                telegram_username="testuser",
                code="A3B7X9",
                db=mock_session_instance
            )

            # Verify linking success response was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            # Should contain success message about linking
            assert "successfully linked" in call_args[0][0].lower() or "linked" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_help_command_handler(self):
        """Test /help command sends help message with command list."""
        from app.api.telegram_handlers import handle_help_command

        # Mock Update and Context
        mock_update = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call handler
        await handle_help_command(mock_update, mock_context)

        # Verify help message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        help_text = call_args[0][0]
        assert "/start" in help_text
        assert "/help" in help_text
        assert "/test" in help_text
        assert call_args[1]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_test_command_handler(self):
        """Test /test command sends confirmation with user's Telegram ID."""
        from app.api.telegram_handlers import handle_test_command

        # Mock Update and Context
        mock_update = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.effective_user.username = "testuser"
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call handler
        await handle_test_command(mock_update, mock_context)

        # Verify test confirmation was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        test_text = call_args[0][0]
        assert "Test successful" in test_text
        assert "123456789" in test_text
        assert call_args[1]["parse_mode"] == "Markdown"
