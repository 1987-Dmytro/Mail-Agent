"""Batch notification background tasks.

This module contains Celery tasks for sending daily batch notifications
to users summarizing pending emails that need approval. Tasks run on
a configurable schedule via Celery Beat (default: daily at 18:00 UTC).
"""

import asyncio
import time
from typing import List, Tuple

import structlog
from celery import shared_task
from sqlmodel import select

from app.models.notification_preferences import NotificationPreferences
from app.models.user import User
from app.services.batch_notification import BatchNotificationService
from app.services.database import database_service

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, time_limit=600, soft_time_limit=570)
def send_batch_notifications(self):
    """Send batch notifications to all users with pending emails (AC #1).

    This task:
    1. Queries all active users with batch_enabled=True
    2. For each user, processes batch notification via BatchNotificationService
    3. Logs batch completion with metrics (AC #9)
    4. Continues processing remaining users even if one user's batch fails

    Scheduled by Celery Beat (default: daily at 18:00 UTC).

    Args:
        self: Celery task instance (injected by bind=True)

    Returns:
        Dict with task execution summary:
            - total_users: Number of users processed
            - total_emails_sent: Total individual proposals sent
            - successful_batches: Number of successful user batches
            - failed_batches: Number of failed user batches

    Raises:
        Exception: Re-raises non-retryable errors after logging
    """
    start_time = time.time()
    logger.info("batch_notifications_started")

    # Create new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Execute batch notification logic
        stats = loop.run_until_complete(_send_batch_notifications_async())

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "batch_notifications_finished",
            total_users=stats["total_users"],
            total_emails_sent=stats["total_emails_sent"],
            successful_batches=stats["successful_batches"],
            failed_batches=stats["failed_batches"],
            duration_ms=duration_ms,
        )

        return stats

    except Exception as e:
        # Unexpected error - log with context
        logger.error(
            "batch_notifications_task_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise

    finally:
        # Always cleanup event loop to prevent resource leaks
        loop.close()


async def _send_batch_notifications_async() -> dict:
    """Execute batch notifications for all users asynchronously.

    Returns:
        Dict with execution statistics
    """
    async with database_service.async_session() as db:
        # Get all active users with batch_enabled=True
        users = await _get_batch_enabled_users(db)

        total_users = len(users)
        total_emails_sent = 0
        successful_batches = 0
        failed_batches = 0

        # Process batch for each user
        for user in users:
            try:
                service = BatchNotificationService(db)
                result = await service.process_batch_for_user(user.id)

                if result["status"] == "completed":
                    total_emails_sent += result["emails_sent"]
                    successful_batches += 1

                    # Log batch completion (AC #9)
                    logger.info(
                        "batch_notification_completed",
                        user_id=user.id,
                        emails_sent=result["emails_sent"],
                        pending_count=result.get("pending_count", 0),
                        status=result["status"]
                    )
                else:
                    # User skipped (disabled, quiet hours, or no emails)
                    logger.info(
                        "batch_notification_skipped",
                        user_id=user.id,
                        status=result["status"]
                    )

            except Exception as e:
                failed_batches += 1
                logger.error(
                    "batch_notification_failed",
                    user_id=user.id,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )

        return {
            "total_users": total_users,
            "total_emails_sent": total_emails_sent,
            "successful_batches": successful_batches,
            "failed_batches": failed_batches,
        }


async def _get_batch_enabled_users(db) -> List[User]:
    """Query all users with batch notifications enabled.

    Args:
        db: Async database session

    Returns:
        List of User objects with batch_enabled=True
    """
    stmt = (
        select(User)
        .join(NotificationPreferences)
        .where(
            NotificationPreferences.batch_enabled == True,  # noqa: E712
            User.is_active == True  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@shared_task(bind=True, max_retries=3, default_retry_delay=60, time_limit=1800, soft_time_limit=1770)
def send_daily_digest(self):
    """Send daily digest of non-priority emails from BatchNotificationQueue (Story 2.3).

    This task processes all pending batch notifications that were queued during
    the day when non-priority emails arrived. It:
    1. Groups pending notifications by user
    2. Sends a summary message with count breakdown
    3. Sends individual proposal messages for each email
    4. Marks notifications as sent in BatchNotificationQueue

    Scheduled by Celery Beat (default: daily at 18:00 UTC).

    Args:
        self: Celery task instance (injected by bind=True)

    Returns:
        Dict with task execution summary:
            - total_users: Number of users processed
            - total_emails_sent: Total notifications sent
            - successful: Number of successful sends
            - failed: Number of failed sends

    Raises:
        Exception: Re-raises non-retryable errors after logging
    """
    start_time = time.time()
    logger.info("daily_digest_started")

    # Create new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Execute daily digest logic
        stats = loop.run_until_complete(_send_daily_digest_async())

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "daily_digest_finished",
            total_users=stats["total_users"],
            total_emails_sent=stats["total_emails_sent"],
            successful=stats["successful"],
            failed=stats["failed"],
            duration_ms=duration_ms,
        )

        return stats

    except Exception as e:
        logger.error(
            "daily_digest_task_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise

    finally:
        # Always cleanup event loop to prevent resource leaks
        loop.close()


async def _send_daily_digest_async() -> dict:
    """Execute daily digest sending for all users asynchronously (Story 2.3).

    Uses SELECT FOR UPDATE SKIP LOCKED to ensure atomic status transitions
    and prevent duplicate processing by concurrent workers.

    Returns:
        Dict with execution statistics
    """
    from app.models.batch_notification_queue import BatchNotificationQueue, BatchNotificationStatus
    from app.core.telegram_bot import TelegramBotClient
    from app.models.workflow_mapping import WorkflowMapping
    from datetime import date, datetime
    import json

    async with database_service.async_session() as db:
        # Get all pending batch notifications scheduled for today or earlier
        # with_for_update(skip_locked=True) ensures:
        # 1. Rows are locked for this transaction (prevents concurrent access)
        # 2. Already locked rows are skipped (prevents blocking/deadlock)
        # 3. Only one worker processes each notification (atomic status transition)
        stmt = select(BatchNotificationQueue).where(
            BatchNotificationQueue.status == BatchNotificationStatus.PENDING.value,
            BatchNotificationQueue.scheduled_for <= date.today()
        ).order_by(
            BatchNotificationQueue.user_id,
            BatchNotificationQueue.created_at
        ).with_for_update(skip_locked=True)
        result = await db.execute(stmt)
        pending_notifications = list(result.scalars().all())

        if not pending_notifications:
            logger.info("no_pending_batch_notifications")
            return {
                "total_users": 0,
                "total_emails_sent": 0,
                "successful": 0,
                "failed": 0
            }

        # Group by user
        notifications_by_user = {}
        for notif in pending_notifications:
            if notif.user_id not in notifications_by_user:
                notifications_by_user[notif.user_id] = []
            notifications_by_user[notif.user_id].append(notif)

        total_users = len(notifications_by_user)
        total_emails_sent = 0
        successful = 0
        failed = 0

        telegram_bot = TelegramBotClient()
        await telegram_bot.initialize()

        # Process each user's batch
        for user_id, notifications in notifications_by_user.items():
            try:
                # Send summary message
                summary = _create_digest_summary(notifications)
                first_notif = notifications[0]

                await telegram_bot.send_message(
                    telegram_id=first_notif.telegram_id,
                    text=summary
                )

                # Send individual notifications
                for notif in notifications:
                    try:
                        # Deserialize buttons
                        buttons = json.loads(notif.buttons_json) if notif.buttons_json else []

                        # Send message with buttons
                        telegram_message_id = await telegram_bot.send_message_with_buttons(
                            telegram_id=notif.telegram_id,
                            text=notif.message_text,
                            buttons=buttons
                        )

                        # Update WorkflowMapping with telegram_message_id
                        stmt = select(WorkflowMapping).where(WorkflowMapping.email_id == notif.email_id)
                        result = await db.execute(stmt)
                        workflow_mapping = result.scalar_one_or_none()

                        if workflow_mapping:
                            workflow_mapping.telegram_message_id = telegram_message_id
                            workflow_mapping.workflow_state = "awaiting_approval"

                        # Mark notification as sent
                        notif.status = BatchNotificationStatus.SENT.value
                        notif.sent_at = datetime.now()

                        successful += 1
                        total_emails_sent += 1

                        # Rate limiting
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(
                            "batch_notification_send_failed",
                            email_id=notif.email_id,
                            error=str(e)
                        )
                        notif.status = BatchNotificationStatus.FAILED.value
                        failed += 1

                await db.commit()

                logger.info(
                    "user_digest_sent",
                    user_id=user_id,
                    emails_sent=len(notifications)
                )

            except Exception as e:
                logger.error(
                    "user_digest_failed",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True
                )

                # Rollback inconsistent state
                await db.rollback()

                # Try to save failed status in separate transaction
                try:
                    for notif in notifications:
                        if notif.status == BatchNotificationStatus.PENDING.value:
                            notif.status = BatchNotificationStatus.FAILED.value
                            # No sent_at for failed notifications

                    await db.commit()
                    logger.info(
                        "batch_error_status_persisted",
                        user_id=user_id,
                        failed_count=len(notifications)
                    )
                except Exception as persist_error:
                    logger.error(
                        "failed_to_persist_error_status",
                        user_id=user_id,
                        error=str(persist_error)
                    )

                failed += len(notifications)

        return {
            "total_users": total_users,
            "total_emails_sent": total_emails_sent,
            "successful": successful,
            "failed": failed
        }


def _create_digest_summary(notifications: List) -> str:
    """Create summary message for daily digest (Story 2.3).

    Args:
        notifications: List of BatchNotificationQueue entries for a user

    Returns:
        Formatted summary message
    """
    total_count = len(notifications)

    summary = f"📬 **Daily Email Summary**\n\n"
    summary += f"You have **{total_count}** non-priority email{'s' if total_count != 1 else ''} needing review.\n\n"
    summary += f"Individual proposals will follow below."

    return summary
