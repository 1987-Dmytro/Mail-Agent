"""Admin alerting utilities (Story 3.2).

This module provides utilities for sending critical alerts to system administrators
via Telegram when errors or issues occur in the system.
"""

import os
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


async def send_admin_alert(
    message: str,
    severity: str = "error",
    context: Optional[dict] = None,
    send_telegram: bool = True
) -> bool:
    """Send an alert to system administrators (Story 3.2).

    This function sends critical alerts to admins when system errors occur.
    By default, alerts are sent via Telegram to the configured admin chat ID.

    Args:
        message: The alert message to send
        severity: Alert severity level ("info", "warning", "error", "critical")
        context: Optional dictionary with additional context (error details, stack traces, etc.)
        send_telegram: Whether to send via Telegram (default: True)

    Returns:
        bool: True if alert was sent successfully, False otherwise

    Example:
        >>> await send_admin_alert(
        ...     "Database connection failed",
        ...     severity="critical",
        ...     context={"error": str(e), "attempts": 3}
        ... )
    """
    # Format the alert message
    severity_emoji = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🚨"
    }
    emoji = severity_emoji.get(severity, "⚠️")

    formatted_message = f"{emoji} **{severity.upper()}**\n\n{message}"

    # Add context if provided
    if context:
        formatted_message += "\n\n**Context:**\n"
        for key, value in context.items():
            formatted_message += f"- {key}: {value}\n"

    # Log the alert
    logger.bind(
        severity=severity,
        message=message,
        context=context
    ).error("admin_alert_triggered")

    # Send via Telegram if enabled
    if send_telegram:
        try:
            admin_chat_id = os.getenv("ADMIN_TELEGRAM_CHAT_ID")

            if not admin_chat_id:
                logger.warning("admin_telegram_chat_id_not_configured")
                return False

            # Import here to avoid circular dependencies
            from app.core.telegram_bot import TelegramBotClient

            telegram_bot = TelegramBotClient()
            await telegram_bot.initialize()

            await telegram_bot.send_message(
                telegram_id=admin_chat_id,
                text=formatted_message
            )

            logger.info("admin_alert_sent_via_telegram", chat_id=admin_chat_id)
            return True

        except Exception as e:
            logger.error(
                "failed_to_send_admin_alert",
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    return True  # Alert logged successfully even if not sent via Telegram
