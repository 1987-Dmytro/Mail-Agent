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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
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

    try:
        # Run async operations in event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

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


async def _send_batch_notifications_async() -> dict:
    """Execute batch notifications for all users asynchronously.

    Returns:
        Dict with execution statistics
    """
    async with database_service.get_session() as db:
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
