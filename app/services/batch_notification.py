"""Batch notification service for daily email summary notifications.

This service handles:
- Retrieving pending emails awaiting approval for each user
- Creating summary messages with category breakdown
- Sending batch notifications via Telegram
- Respecting user preferences (quiet hours, batch timing)
- Handling empty batches (no notification sent)
"""

import asyncio
from datetime import datetime, time
from typing import Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.notification_preferences import NotificationPreferences
from app.models.user import User
from app.services.telegram_message_formatter import (
    create_inline_keyboard,
    format_sorting_proposal_message,
)

logger = structlog.get_logger(__name__)


class BatchNotificationService:
    """Service for daily batch email notifications.

    Processes batch notifications for users, sending:
    1. Summary message showing count and category breakdown
    2. Individual proposal messages for each pending email

    Respects user preferences:
    - batch_enabled: Global toggle
    - quiet_hours: Suppresses notifications during configured hours
    - batch_time: Preferred notification time (future enhancement)
    """

    def __init__(self, db: AsyncSession):
        """Initialize batch notification service.

        Args:
            db: Async database session for queries
        """
        self.db = db
        self.telegram_bot = TelegramBotClient()
        self.logger = structlog.get_logger()

    async def process_batch_for_user(self, user_id: int) -> Dict:
        """Process batch notification for a single user.

        Main orchestration method that:
        1. Loads user preferences
        2. Checks batch enabled and quiet hours
        3. Queries pending emails
        4. Sends summary message
        5. Sends individual proposal messages

        Args:
            user_id: User ID to process batch for

        Returns:
            Dict with processing results:
                - status: "disabled" | "quiet_hours" | "no_emails" | "completed"
                - emails_sent: Number of individual proposal messages sent
                - pending_count: Total number of pending emails (if completed)

        Example:
            >>> result = await service.process_batch_for_user(user_id=42)
            >>> print(result)
            {"status": "completed", "emails_sent": 5, "pending_count": 5}
        """
        # Load user preferences
        prefs = await self.get_user_preferences(user_id)

        # Check if batch enabled (AC #7)
        if not prefs.batch_enabled:
            self.logger.info("batch_processing_disabled", user_id=user_id)
            return {"status": "disabled", "emails_sent": 0}

        # Check quiet hours
        if self.is_quiet_hours(prefs):
            self.logger.info("batch_processing_quiet_hours", user_id=user_id)
            return {"status": "quiet_hours", "emails_sent": 0}

        # Query pending emails (AC #2)
        pending_emails = await self.get_pending_emails(user_id)

        # Empty batch handling (AC #8)
        if not pending_emails:
            self.logger.info("batch_processing_no_emails", user_id=user_id)
            return {"status": "no_emails", "emails_sent": 0}

        # Create summary message (AC #3, #4)
        summary = self.create_summary_message(pending_emails)

        # Send summary message
        await self.send_summary(user_id, summary)

        # Send individual proposal messages (AC #5)
        sent_count = await self.send_individual_proposals(user_id, pending_emails)

        self.logger.info(
            "batch_processing_completed",
            user_id=user_id,
            pending_count=len(pending_emails),
            emails_sent=sent_count,
        )

        return {
            "status": "completed",
            "emails_sent": sent_count,
            "pending_count": len(pending_emails)
        }

    async def get_user_preferences(self, user_id: int) -> NotificationPreferences:
        """Retrieve notification preferences for user.

        If user has no preferences, creates default preferences.

        Args:
            user_id: User ID to load preferences for

        Returns:
            NotificationPreferences instance with user settings

        Raises:
            ValueError: If user does not exist
        """
        stmt = select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )
        result = await self.db.execute(stmt)
        prefs = result.scalar_one_or_none()

        if prefs is None:
            # Create default preferences for user
            prefs = NotificationPreferences(
                user_id=user_id,
                batch_enabled=True,
                batch_time=time(18, 0),
                priority_immediate=True,
                timezone="UTC"
            )
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(prefs)

            self.logger.info(
                "notification_preferences_created",
                user_id=user_id,
                batch_time="18:00"
            )

        return prefs

    async def get_pending_emails(self, user_id: int) -> List[EmailProcessingQueue]:
        """Retrieve all pending emails awaiting approval (AC #2).

        Filters for:
        - User's emails only
        - Status = "awaiting_approval"
        - is_priority = False (priority emails sent immediately)

        Orders by:
        - received_at ASC (oldest first)

        Args:
            user_id: User ID to query emails for

        Returns:
            List of EmailProcessingQueue objects awaiting approval
        """
        stmt = (
            select(EmailProcessingQueue)
            .where(
                EmailProcessingQueue.user_id == user_id,
                EmailProcessingQueue.status == "awaiting_approval",
                EmailProcessingQueue.is_priority == False  # noqa: E712
            )
            .order_by(EmailProcessingQueue.received_at.asc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def is_quiet_hours(self, prefs: NotificationPreferences) -> bool:
        """Check if current time is within user's quiet hours.

        Quiet hours suppress batch notifications during configured time window.

        Args:
            prefs: User notification preferences

        Returns:
            True if current time is within quiet hours, False otherwise

        Example:
            - quiet_hours_start = 22:00, quiet_hours_end = 08:00
            - Current time 23:30 → True (within quiet hours)
            - Current time 10:00 → False (outside quiet hours)
        """
        if prefs.quiet_hours_start is None or prefs.quiet_hours_end is None:
            return False

        now = datetime.now().time()
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end

        # Handle overnight quiet hours (e.g., 22:00 - 08:00)
        if start > end:
            return now >= start or now <= end
        # Handle same-day quiet hours (e.g., 01:00 - 06:00)
        else:
            return start <= now <= end

    def create_summary_message(self, pending_emails: List[EmailProcessingQueue]) -> str:
        """Create batch summary message (AC #3, #4).

        Formats:
        - Total count of pending emails
        - Breakdown by proposed category (sorted by count descending)

        Args:
            pending_emails: List of pending emails

        Returns:
            Formatted summary message with Markdown

        Example:
            📬 **Daily Email Summary**

            You have **8** emails needing review:

            • 3 → Government
            • 2 → Clients
            • 2 → Newsletters
            • 1 → Personal

            Individual proposals will follow below.
        """
        total_count = len(pending_emails)

        # Count by category (AC #4)
        category_counts = {}
        for email in pending_emails:
            if email.proposed_folder:  # Check if folder exists
                folder_name = email.proposed_folder.name
                category_counts[folder_name] = category_counts.get(folder_name, 0) + 1

        # Format summary message
        summary = f"📬 **Daily Email Summary**\n\n"
        summary += f"You have **{total_count}** emails needing review:\n\n"

        # Sort by count descending, then alphabetically
        for folder_name, count in sorted(category_counts.items(), key=lambda x: (-x[1], x[0])):
            summary += f"• {count} → {folder_name}\n"

        summary += f"\nIndividual proposals will follow below."

        return summary

    async def send_summary(self, user_id: int, summary: str) -> None:
        """Send batch summary message to user via Telegram.

        Args:
            user_id: User ID to send summary to
            summary: Formatted summary message

        Raises:
            Exception: If user has no telegram_id or message sending fails
        """
        # Load user to get telegram_id
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.telegram_id:
            self.logger.error("batch_summary_send_failed_no_telegram_id", user_id=user_id)
            raise ValueError(f"User {user_id} has no telegram_id")

        # Send summary message (no buttons needed)
        try:
            message_id = await self.telegram_bot.send_message(
                telegram_id=user.telegram_id,
                text=summary
            )

            self.logger.info(
                "batch_summary_sent",
                user_id=user_id,
                telegram_id=user.telegram_id,
                message_id=message_id
            )

        except Exception as e:
            self.logger.error(
                "batch_summary_send_failed",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def send_individual_proposals(
        self,
        user_id: int,
        pending_emails: List[EmailProcessingQueue]
    ) -> int:
        """Send individual proposal messages for each pending email (AC #5).

        For each email:
        1. Format proposal message using TelegramMessageFormatter
        2. Create inline keyboard buttons
        3. Send message via TelegramBotClient
        4. Update WorkflowMapping with telegram_message_id
        5. Implement rate limiting (100ms delay between sends)

        Args:
            user_id: User ID to send proposals to
            pending_emails: List of pending emails to send proposals for

        Returns:
            Number of successfully sent proposal messages

        Note:
            Continues processing remaining emails even if one fails.
            Rate limiting prevents Telegram API errors (30 msgs/sec, 20 msgs/min per chat).
        """
        # Load user to get telegram_id
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.telegram_id:
            self.logger.error("send_individual_proposals_no_telegram_id", user_id=user_id)
            return 0

        sent_count = 0

        for email in pending_emails:
            try:
                # Format proposal message (reuse existing formatter from Story 2.6)
                # Note: body_preview not available in EmailProcessingQueue,
                # using empty string as placeholder (email body not needed for approval decision)
                body_preview = ""  # Email body preview not stored in queue

                message_text = format_sorting_proposal_message(
                    sender=email.sender,
                    subject=email.subject or "(No subject)",
                    body_preview=body_preview,
                    proposed_folder=email.proposed_folder.name if email.proposed_folder else "Unclassified",
                    reasoning=email.classification_reasoning or "No reasoning provided",
                    is_priority=False  # Non-priority emails only (priority sent immediately)
                )

                # Create inline keyboard buttons
                inline_keyboard = create_inline_keyboard(email.id)

                # Send message with buttons
                telegram_message_id = await self.telegram_bot.send_message_with_buttons(
                    telegram_id=user.telegram_id,
                    text=message_text,
                    buttons=inline_keyboard
                )

                # Update WorkflowMapping with telegram_message_id for callback reconnection
                from app.models.workflow_mapping import WorkflowMapping
                stmt = select(WorkflowMapping).where(WorkflowMapping.email_id == email.id)
                result = await self.db.execute(stmt)
                workflow_mapping = result.scalar_one_or_none()

                if workflow_mapping:
                    workflow_mapping.telegram_message_id = telegram_message_id
                    await self.db.commit()
                    self.logger.debug(
                        "workflow_mapping_updated_with_telegram_id",
                        email_id=email.id,
                        telegram_message_id=telegram_message_id
                    )
                else:
                    self.logger.warning(
                        "workflow_mapping_not_found",
                        email_id=email.id,
                        note="WorkflowMapping should exist for awaiting_approval emails"
                    )

                sent_count += 1

                self.logger.info(
                    "individual_proposal_sent",
                    email_id=email.id,
                    user_id=user_id,
                    telegram_message_id=telegram_message_id
                )

                # Rate limiting: Wait 100ms between messages to avoid Telegram limits
                # (Telegram limits: 30 msgs/sec, 20 msgs/min per chat)
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(
                    "individual_proposal_send_failed",
                    email_id=email.id,
                    user_id=user_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                # Continue with remaining emails even if one fails

        return sent_count
