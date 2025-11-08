"""Telegram Bot Client wrapper for Mail Agent.

This module provides a high-level interface for interacting with the Telegram Bot API
using python-telegram-bot library. It handles bot initialization, message sending,
and command/callback handling.
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, NetworkError, TelegramError, TimedOut
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from app.core.config import settings
from app.utils.errors import TelegramBotError, TelegramSendError, TelegramUserBlockedError
from app.utils.retry import execute_with_retry

logger = structlog.get_logger(__name__)


class TelegramBotClient:
    """Telegram Bot API client wrapper.

    Provides methods for:
    - Bot initialization and connection
    - Sending messages to users
    - Sending messages with inline keyboard buttons
    - Registering command and callback handlers
    - Long polling for updates
    """

    def __init__(self):
        """Initialize Telegram bot client.

        Loads bot token from settings and prepares application instance.
        Does not start the bot connection - call initialize() for that.
        """
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application: Application | None = None
        self.bot = None
        logger.info("telegram_bot_client_created")

    async def initialize(self):
        """Initialize the bot application and register handlers.

        Builds the Application instance, gets bot reference, and registers
        command handlers. Must be called before start_polling().

        Raises:
            TelegramBotError: If bot token is invalid or initialization fails
        """
        if not self.token:
            error_msg = "TELEGRAM_BOT_TOKEN not configured in environment variables"
            logger.error("telegram_bot_initialization_failed", error=error_msg)
            raise TelegramBotError(error_msg)

        try:
            # Build application with bot token
            self.application = Application.builder().token(self.token).build()
            self.bot = self.application.bot

            # Import handlers here to avoid circular imports
            from app.api.telegram_handlers import (
                handle_callback_query,
                handle_help_command,
                handle_retry_command,
                handle_start_command,
                handle_test_command,
            )

            # Register command handlers
            self.application.add_handler(CommandHandler("start", handle_start_command))
            self.application.add_handler(CommandHandler("help", handle_help_command))
            self.application.add_handler(CommandHandler("test", handle_test_command))
            self.application.add_handler(CommandHandler("retry", handle_retry_command))  # Story 2.11

            # Register callback query handler (Story 2.7)
            self.application.add_handler(CallbackQueryHandler(handle_callback_query))

            # Initialize application
            await self.application.initialize()

            logger.info("telegram_bot_initialized", bot_username=self.bot.username)

        except TelegramError as e:
            logger.error("telegram_bot_initialization_failed", error=str(e), error_type=type(e).__name__)
            raise TelegramBotError(f"Failed to initialize Telegram bot: {str(e)}") from e

    async def send_message(self, telegram_id: str, text: str, user_id: int = None) -> str:
        """Send a text message to a specific Telegram user with retry logic.

        Uses exponential backoff for transient errors (network, timeout).
        Does NOT retry for permanent errors (403 Forbidden - user blocked bot).
        Auto-truncates messages exceeding 4000 characters.

        Args:
            telegram_id: Telegram user ID (chat_id)
            text: Message text (supports Markdown formatting)
            user_id: Optional database user_id for enhanced logging

        Returns:
            str: Message ID of the sent message

        Raises:
            ValueError: If telegram_id format is invalid
            TelegramUserBlockedError: If user has blocked the bot (permanent error, no retry)
            TelegramSendError: If message sending fails after retries exhausted
        """
        if not self.bot:
            raise TelegramBotError("Bot not initialized. Call initialize() first.")

        # Validate telegram_id format (must be digits only)
        if not telegram_id.isdigit():
            raise ValueError(f"Invalid telegram_id format: '{telegram_id}'. Must contain only digits.")

        # Auto-truncate long messages (Story 2.11 - AC #2)
        original_length = len(text)
        if len(text) > 4096:
            # Truncate to 4000 chars with "..." indicator (leave buffer)
            text = text[:4000] + "..."
            logger.info(
                "telegram_message_truncated",
                telegram_id=telegram_id,
                original_length=original_length,
                truncated_length=len(text),
            )

        async def _send():
            return await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

        try:
            # Check for user blocked scenario first (permanent error, no retry)
            try:
                message = await execute_with_retry(_send)

                logger.info(
                    "telegram_message_sent",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    message_id=message.message_id,
                    message_length=len(text),
                    operation="send_message",
                )

                return str(message.message_id)

            except Forbidden as e:
                # User blocked bot - permanent error, do NOT retry
                logger.error(
                    "telegram_api_error",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    error_type="forbidden",
                    error_message=str(e),
                    operation="send_message",
                )
                logger.error(
                    "telegram_user_blocked_bot",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    error=str(e),
                )
                raise TelegramUserBlockedError(f"User {telegram_id} has blocked the bot") from e

        except (NetworkError, TimedOut, TelegramSendError) as e:
            # Retries exhausted for transient errors
            logger.error(
                "telegram_api_error",
                telegram_id=telegram_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                operation="send_message",
                exc_info=True,
            )
            raise TelegramSendError(f"Failed to send message to {telegram_id} after retries: {str(e)}") from e

        except TelegramError as e:
            # Other Telegram errors
            logger.error(
                "telegram_api_error",
                telegram_id=telegram_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                operation="send_message",
                exc_info=True,
            )
            raise TelegramSendError(f"Failed to send message to {telegram_id}: {str(e)}") from e

    async def send_message_with_buttons(
        self,
        telegram_id: str,
        text: str,
        buttons: list[list[InlineKeyboardButton]],
        user_id: int = None,
    ) -> str:
        """Send a message with inline keyboard buttons and retry logic.

        Uses exponential backoff for transient errors (network, timeout).
        Does NOT retry for permanent errors (403 Forbidden - user blocked bot).
        Auto-truncates messages exceeding 4000 characters.

        Args:
            telegram_id: Telegram user ID (chat_id)
            text: Message text (supports Markdown formatting)
            buttons: 2D list of InlineKeyboardButton objects
                    Each inner list represents a row of buttons
            user_id: Optional database user_id for enhanced logging

        Returns:
            str: Message ID of the sent message

        Raises:
            ValueError: If telegram_id format is invalid
            TelegramUserBlockedError: If user has blocked the bot (permanent error, no retry)
            TelegramSendError: If message sending fails after retries exhausted
        """
        if not self.bot:
            raise TelegramBotError("Bot not initialized. Call initialize() first.")

        # Validate telegram_id format (must be digits only)
        if not telegram_id.isdigit():
            raise ValueError(f"Invalid telegram_id format: '{telegram_id}'. Must contain only digits.")

        # Auto-truncate long messages (Story 2.11 - AC #2)
        original_length = len(text)
        if len(text) > 4096:
            # Truncate to 4000 chars with "..." indicator (leave buffer)
            text = text[:4000] + "..."
            logger.info(
                "telegram_message_truncated",
                telegram_id=telegram_id,
                original_length=original_length,
                truncated_length=len(text),
            )

        async def _send():
            reply_markup = InlineKeyboardMarkup(buttons)
            return await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

        try:
            # Check for user blocked scenario first (permanent error, no retry)
            try:
                message = await execute_with_retry(_send)

                logger.info(
                    "telegram_message_with_buttons_sent",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    message_id=message.message_id,
                    button_count=sum(len(row) for row in buttons),
                    operation="send_message_with_buttons",
                )

                return str(message.message_id)

            except Forbidden as e:
                # User blocked bot - permanent error, do NOT retry
                logger.error(
                    "telegram_api_error",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    error_type="forbidden",
                    error_message=str(e),
                    operation="send_message_with_buttons",
                )
                logger.error(
                    "telegram_user_blocked_bot",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    error=str(e),
                )
                raise TelegramUserBlockedError(f"User {telegram_id} has blocked the bot") from e

        except (NetworkError, TimedOut, TelegramSendError) as e:
            # Retries exhausted for transient errors
            logger.error(
                "telegram_api_error",
                telegram_id=telegram_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                operation="send_message_with_buttons",
                exc_info=True,
            )
            raise TelegramSendError(f"Failed to send message to {telegram_id} after retries: {str(e)}") from e

        except TelegramError as e:
            # Other Telegram errors
            logger.error(
                "telegram_api_error",
                telegram_id=telegram_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                operation="send_message_with_buttons",
                exc_info=True,
            )
            raise TelegramSendError(f"Failed to send message to {telegram_id}: {str(e)}") from e

    async def edit_message_text(
        self,
        telegram_id: str,
        message_id: str,
        text: str,
    ) -> bool:
        """Edit an existing Telegram message text (Story 2.7).

        Used for updating approval messages with confirmation after user decision.

        Args:
            telegram_id: Telegram user ID (chat_id)
            message_id: Message ID to edit (from WorkflowMapping.telegram_message_id)
            text: New message text (supports Markdown formatting)

        Returns:
            bool: True if edit successful, False otherwise

        Raises:
            ValueError: If telegram_id format is invalid or message exceeds 4096 characters
            TelegramSendError: If message edit fails
        """
        if not self.bot:
            raise TelegramBotError("Bot not initialized. Call initialize() first.")

        # Validate telegram_id format (must be digits only)
        if not telegram_id.isdigit():
            raise ValueError(f"Invalid telegram_id format: '{telegram_id}'. Must contain only digits.")

        # Validate message length (Telegram API limit: 4096 characters)
        if len(text) > 4096:
            raise ValueError(f"Message exceeds 4096 character limit (current length: {len(text)})")

        try:
            await self.bot.edit_message_text(
                chat_id=telegram_id,
                message_id=int(message_id),
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

            logger.info(
                "telegram_message_edited",
                telegram_id=telegram_id,
                message_id=message_id,
            )

            return True

        except TelegramError as e:
            logger.error(
                "telegram_edit_message_failed",
                telegram_id=telegram_id,
                message_id=message_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise TelegramSendError(f"Failed to edit message {message_id}: {str(e)}") from e

    async def start_polling(self):
        """Start the bot with long polling (getUpdates mode).

        Begins polling Telegram servers for updates (messages, commands, button clicks).
        This is a non-blocking call that starts background polling.

        Updates handled:
        - message: Text messages from users
        - callback_query: Inline button clicks

        Raises:
            TelegramBotError: If polling fails to start
        """
        if not self.application:
            raise TelegramBotError("Application not initialized. Call initialize() first.")

        try:
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
            )
            logger.info("telegram_bot_started", mode="long_polling")

        except TelegramError as e:
            logger.error("telegram_polling_start_failed", error=str(e))
            raise TelegramBotError(f"Failed to start polling: {str(e)}") from e

    async def stop_polling(self):
        """Stop the bot gracefully.

        Stops polling for updates and shuts down the application cleanly.
        Should be called during application shutdown.
        """
        if not self.application:
            logger.warning("telegram_bot_stop_called_but_not_initialized")
            return

        try:
            if self.application.updater and self.application.updater.running:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("telegram_bot_stopped")

        except Exception as e:
            logger.error("telegram_bot_stop_failed", error=str(e))
            # Don't raise - shutdown should be graceful even if errors occur
