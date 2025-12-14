"""Telegram Bot Client wrapper for Mail Agent.

This module provides a high-level interface for interacting with the Telegram Bot API
using python-telegram-bot library. It handles bot initialization, message sending,
and command/callback handling.
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Forbidden, NetworkError, TelegramError, TimedOut
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
                handle_message,
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

            # Register message handler for edit workflow (Story 3.9)
            from telegram.ext import MessageHandler, filters
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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

        Epic 1 - Story 1.1: Implements markdown escaping with fallback to plain text.

        Args:
            telegram_id: Telegram user ID (chat_id)
            text: Message text (will be escaped for MarkdownV2)
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
        from app.utils.telegram_markdown import escape_markdown, strip_markdown

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

        # Story 1.1: Try MarkdownV2 with proper escaping first, fallback to plain text
        reply_markup = InlineKeyboardMarkup(buttons)

        # FALLBACK LEVEL 1: Try with escaped MarkdownV2
        try:
            escaped_text = escape_markdown(text, version=2)

            async def _send_markdown():
                return await self.bot.send_message(
                    chat_id=telegram_id,
                    text=escaped_text,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True,
                )

            try:
                message = await execute_with_retry(_send_markdown)

                logger.info(
                    "telegram_message_with_buttons_sent",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    message_id=message.message_id,
                    button_count=sum(len(row) for row in buttons),
                    parse_mode="MarkdownV2",
                    operation="send_message_with_buttons",
                )

                return str(message.message_id)

            except Forbidden as e:
                # User blocked bot - permanent error, do NOT retry
                logger.error(
                    "telegram_user_blocked_bot",
                    telegram_id=telegram_id,
                    user_id=user_id,
                    error=str(e),
                )
                raise TelegramUserBlockedError(f"User {telegram_id} has blocked the bot") from e

            except BadRequest as e:
                # Markdown parsing error - try fallback to plain text
                if "can't parse entities" in str(e).lower() or "can't find end" in str(e).lower():
                    logger.warning(
                        "telegram_markdown_parsing_failed_fallback_to_plain",
                        telegram_id=telegram_id,
                        user_id=user_id,
                        error=str(e),
                        fallback="plain_text",
                    )
                    # FALLBACK LEVEL 2: Plain text without markdown
                    plain_text = strip_markdown(text)

                    async def _send_plain():
                        return await self.bot.send_message(
                            chat_id=telegram_id,
                            text=plain_text,
                            reply_markup=reply_markup,
                            parse_mode=None,  # No markdown
                            disable_web_page_preview=True,
                        )

                    try:
                        message = await execute_with_retry(_send_plain)

                        logger.info(
                            "telegram_message_with_buttons_sent_plain_text_fallback",
                            telegram_id=telegram_id,
                            user_id=user_id,
                            message_id=message.message_id,
                            button_count=sum(len(row) for row in buttons),
                            parse_mode=None,
                            operation="send_message_with_buttons",
                        )

                        return str(message.message_id)

                    except Exception as plain_error:
                        # Plain text also failed - propagate error
                        logger.error(
                            "telegram_plain_text_fallback_failed",
                            telegram_id=telegram_id,
                            user_id=user_id,
                            error=str(plain_error),
                        )
                        raise TelegramSendError(
                            f"Failed to send message to {telegram_id} (both MarkdownV2 and plain text failed)"
                        ) from plain_error
                else:
                    # Other BadRequest error, not markdown related
                    raise

        except (NetworkError, TimedOut) as e:
            # Retries exhausted for transient errors
            logger.error(
                "telegram_api_error_network_timeout",
                telegram_id=telegram_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                operation="send_message_with_buttons",
                exc_info=True,
            )
            raise TelegramSendError(f"Failed to send message to {telegram_id} after retries: {str(e)}") from e

        except TelegramUserBlockedError:
            # Re-raise user blocked error (already logged above)
            raise

        except TelegramSendError:
            # Re-raise send errors (already logged above)
            raise

        except TelegramError as e:
            # Other Telegram errors
            logger.error(
                "telegram_api_error_other",
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
                # NOTE: No parse_mode - using plain text to avoid parsing errors
                # with special characters in sender/subject fields
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

    async def delete_message(
        self,
        telegram_id: str,
        message_id: str,
    ) -> bool:
        """Delete a Telegram message.

        Used for cleaning up intermediate messages (sorting proposal, draft notification)
        before sending final summary message.

        Args:
            telegram_id: Telegram user ID (chat_id)
            message_id: Message ID to delete

        Returns:
            bool: True if deletion successful, False otherwise

        Raises:
            ValueError: If telegram_id format is invalid
            TelegramSendError: If message deletion fails
        """
        if not self.bot:
            raise TelegramBotError("Bot not initialized. Call initialize() first.")

        # Validate telegram_id format (must be digits only)
        if not telegram_id.isdigit():
            raise ValueError(f"Invalid telegram_id format: '{telegram_id}'. Must contain only digits.")

        try:
            await self.bot.delete_message(
                chat_id=telegram_id,
                message_id=int(message_id),
            )

            logger.info(
                "telegram_message_deleted",
                telegram_id=telegram_id,
                message_id=message_id,
            )

            return True

        except TelegramError as e:
            # Don't raise error - deletion failure is not critical
            # Message might already be deleted or not exist
            logger.warning(
                "telegram_delete_message_failed",
                telegram_id=telegram_id,
                message_id=message_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False

    async def set_webhook(self, webhook_url: str, secret_token: str = None):
        """Configure Telegram webhook for production deployments.

        Sets up Telegram to send updates to the specified webhook URL.
        This is the recommended approach for production with multiple instances.

        Args:
            webhook_url: Full HTTPS URL where Telegram will send updates
            secret_token: Optional secret token for webhook validation

        Raises:
            TelegramBotError: If webhook setup fails
        """
        if not self.bot:
            raise TelegramBotError("Bot not initialized. Call initialize() first.")

        try:
            await self.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
                secret_token=secret_token,
            )
            logger.info(
                "telegram_webhook_set",
                webhook_url=webhook_url,
                has_secret=bool(secret_token),
            )

        except TelegramError as e:
            logger.error("telegram_webhook_setup_failed", error=str(e), webhook_url=webhook_url)
            raise TelegramBotError(f"Failed to set webhook: {str(e)}") from e

    async def delete_webhook(self):
        """Remove webhook and switch back to polling mode.

        Useful for local development or when switching from production to development.

        Raises:
            TelegramBotError: If webhook deletion fails
        """
        if not self.bot:
            raise TelegramBotError("Bot not initialized. Call initialize() first.")

        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("telegram_webhook_deleted")

        except TelegramError as e:
            logger.error("telegram_webhook_deletion_failed", error=str(e))
            raise TelegramBotError(f"Failed to delete webhook: {str(e)}") from e

    async def start(self):
        """Start the bot application (for webhook mode).

        Starts the application without polling. Use this when webhooks are configured.
        The application will receive updates via webhook endpoint instead of polling.

        Raises:
            TelegramBotError: If application start fails
        """
        if not self.application:
            raise TelegramBotError("Application not initialized. Call initialize() first.")

        try:
            await self.application.start()
            logger.info("telegram_bot_started", mode="webhook")

        except TelegramError as e:
            logger.error("telegram_bot_start_failed", error=str(e))
            raise TelegramBotError(f"Failed to start bot: {str(e)}") from e

    async def start_polling(self):
        """Start the bot with long polling (getUpdates mode).

        Begins polling Telegram servers for updates (messages, commands, button clicks).
        This is a non-blocking call that starts background polling.

        IMPORTANT: Only use for local development. For production with multiple instances,
        use webhook mode instead to avoid conflicts.

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

    async def stop(self):
        """Stop the bot gracefully (for webhook mode).

        Shuts down the application cleanly without stopping updater.
        Use this for webhook mode shutdown.
        """
        if not self.application:
            logger.warning("telegram_bot_stop_called_but_not_initialized")
            return

        try:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("telegram_bot_stopped", mode="webhook")

        except Exception as e:
            logger.error("telegram_bot_stop_failed", error=str(e))
            # Don't raise - shutdown should be graceful even if errors occur
