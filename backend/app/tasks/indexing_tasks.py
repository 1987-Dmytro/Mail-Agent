"""Celery tasks for email history indexing.

This module provides background tasks for indexing user's Gmail history
into the vector database for RAG context retrieval.

Tasks:
- index_user_emails: Start or resume email history indexing for a user

Configuration:
- Task timeout: 3600 seconds (1 hour) for large mailboxes
- Max retries: 3 with exponential backoff
- Queue: default (shared with email polling tasks)

Usage:
    # Trigger indexing job for user
    index_user_emails.delay(user_id=123, days_back=90)

    # Synchronous call (testing)
    index_user_emails(user_id=123, days_back=90)

Reference: docs/tech-spec-epic-3.md#Email-History-Indexing-Strategy
"""

import structlog
from celery import shared_task
from app.celery import celery_app
from app.services.email_indexing import EmailIndexingService
from app.utils.errors import GmailAPIError, GeminiAPIError

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.indexing_tasks.index_user_emails",
    bind=True,  # Bind task instance to self parameter
    max_retries=3,
    default_retry_delay=60,  # 1 minute between retries
    time_limit=3600,  # 1 hour max execution time
    soft_time_limit=3540,  # 59 minutes soft limit (log warning before hard kill)
)
def index_user_emails(self, user_id: int, days_back: int = 90) -> dict:
    """Index user's email history into vector database.

    This task orchestrates the complete email indexing workflow:
    1. Initialize EmailIndexingService for user
    2. Start indexing (retrieve, embed, store emails)
    3. Handle errors with retry logic
    4. Send Telegram notification on completion

    The task uses exponential backoff retry strategy for transient errors:
    - Gmail API rate limits (429)
    - Gemini API rate limits or timeouts
    - Network connectivity issues

    Permanent errors (invalid user, no Gmail credentials) are not retried.

    Args:
        user_id: Database ID of user to index
        days_back: Number of days to look back (default: 90)

    Returns:
        dict with keys:
        - success: bool
        - user_id: int
        - total_emails: int (if successful)
        - processed: int (if successful)
        - error: str (if failed)

    Raises:
        Exception: Re-raised after max retries exhausted

    Example:
        # Trigger background task
        result = index_user_emails.delay(user_id=123, days_back=90)

        # Check status
        if result.ready():
            print(result.result)  # {'success': True, 'total_emails': 437, ...}
    """
    logger.info(
        "indexing_task_started",
        task_id=self.request.id,
        user_id=user_id,
        days_back=days_back,
    )

    try:
        # Initialize indexing service
        service = EmailIndexingService(user_id=user_id)

        # Start indexing (async operation - need to run in sync context)
        import asyncio

        # Always create a fresh event loop for Celery tasks
        # This avoids "Event loop is closed" errors in worker processes
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            progress = loop.run_until_complete(service.start_indexing(days_back=days_back))
        finally:
            # Clean up the event loop
            loop.close()

        result = {
            "success": True,
            "user_id": user_id,
            "total_emails": progress.total_emails,
            "processed": progress.processed_count,
            "status": progress.status.value,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        }

        logger.info(
            "indexing_task_completed",
            task_id=self.request.id,
            user_id=user_id,
            total_emails=progress.total_emails,
        )

        return result

    except (GmailAPIError, GeminiAPIError) as e:
        # Transient API errors - retry with exponential backoff
        logger.warning(
            "indexing_task_retry",
            task_id=self.request.id,
            user_id=user_id,
            error_type=type(e).__name__,
            error=str(e),
            retry_count=self.request.retries,
            max_retries=self.max_retries,
        )

        # Exponential backoff: 60s, 120s, 240s
        retry_delay = self.default_retry_delay * (2 ** self.request.retries)

        try:
            raise self.retry(exc=e, countdown=retry_delay)
        except Exception as retry_exc:
            # Max retries exhausted - log and re-raise
            logger.error(
                "indexing_task_failed_max_retries",
                task_id=self.request.id,
                user_id=user_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            return {
                "success": False,
                "user_id": user_id,
                "error": f"{type(e).__name__}: {str(e)}",
                "retries_exhausted": True,
            }

    except ValueError as e:
        # Permanent errors (e.g., indexing job already exists) - do not retry
        logger.error(
            "indexing_task_failed_permanent",
            task_id=self.request.id,
            user_id=user_id,
            error_type=type(e).__name__,
            error=str(e),
        )

        return {
            "success": False,
            "user_id": user_id,
            "error": f"{type(e).__name__}: {str(e)}",
            "permanent_error": True,
        }

    except Exception as e:
        # Unexpected errors - log and fail (do not retry)
        logger.exception(
            "indexing_task_unexpected_error",
            task_id=self.request.id,
            user_id=user_id,
            error_type=type(e).__name__,
            error=str(e),
        )

        return {
            "success": False,
            "user_id": user_id,
            "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
        }


@celery_app.task(
    name="app.tasks.indexing_tasks.resume_user_indexing",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=3600,
    soft_time_limit=3540,
)
def resume_user_indexing(self, user_id: int) -> dict:
    """Resume interrupted email indexing job for user.

    This task checks for interrupted indexing jobs and resumes from checkpoint.
    Useful for:
    - Worker restarts or crashes
    - Manual intervention (pause/resume)
    - Network connectivity issues

    Args:
        user_id: Database ID of user

    Returns:
        dict with success status and details

    Example:
        # Resume interrupted job
        result = resume_user_indexing.delay(user_id=123)
    """
    logger.info(
        "resume_indexing_task_started",
        task_id=self.request.id,
        user_id=user_id,
    )

    try:
        service = EmailIndexingService(user_id=user_id)

        import asyncio

        # Always create a fresh event loop for Celery tasks
        # This avoids "Event loop is closed" errors in worker processes
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            progress = loop.run_until_complete(service.resume_indexing())
        finally:
            # Clean up the event loop
            loop.close()

        if not progress:
            return {
                "success": False,
                "user_id": user_id,
                "error": "No interrupted indexing job found",
            }

        result = {
            "success": True,
            "user_id": user_id,
            "total_emails": progress.total_emails,
            "processed": progress.processed_count,
            "status": progress.status.value,
        }

        logger.info(
            "resume_indexing_task_completed",
            task_id=self.request.id,
            user_id=user_id,
            total_emails=progress.total_emails,
        )

        return result

    except Exception as e:
        logger.error(
            "resume_indexing_task_failed",
            task_id=self.request.id,
            user_id=user_id,
            error=str(e),
        )

        return {
            "success": False,
            "user_id": user_id,
            "error": str(e),
        }


@celery_app.task(
    name="app.tasks.indexing_tasks.index_new_email_background",
    bind=True,
    max_retries=2,  # Fewer retries for incremental indexing
    default_retry_delay=30,
    time_limit=120,  # 2 minutes (single email)
)
def index_new_email_background(self, user_id: int, message_id: str) -> dict:
    """Index single new email for incremental indexing (background task).

    This task is triggered by the email polling service when new emails are detected.
    It performs incremental indexing (single email, no batch delay) to keep
    the vector database up-to-date with latest emails.

    Args:
        user_id: Database ID of user
        message_id: Gmail message ID of new email

    Returns:
        dict with success status

    Example:
        # Triggered by email polling service
        index_new_email_background.delay(user_id=123, message_id="abc123")
    """
    logger.info(
        "incremental_indexing_task_started",
        task_id=self.request.id,
        user_id=user_id,
        message_id=message_id,
    )

    import asyncio

    # Create new event loop for this task (Celery worker pool issue)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        service = EmailIndexingService(user_id=user_id)

        success = loop.run_until_complete(service.index_new_email(message_id=message_id))

        if success:
            logger.info(
                "incremental_indexing_task_completed",
                task_id=self.request.id,
                user_id=user_id,
                message_id=message_id,
            )
        else:
            logger.warning(
                "incremental_indexing_task_skipped",
                task_id=self.request.id,
                user_id=user_id,
                message_id=message_id,
                reason="Initial indexing not complete or email already indexed",
            )

        return {
            "success": success,
            "user_id": user_id,
            "message_id": message_id,
        }

    except Exception as e:
        logger.error(
            "incremental_indexing_task_failed",
            task_id=self.request.id,
            user_id=user_id,
            message_id=message_id,
            error=str(e),
        )

        return {
            "success": False,
            "user_id": user_id,
            "message_id": message_id,
            "error": str(e),
        }

    finally:
        # Always cleanup event loop to prevent resource leaks
        loop.close()


@celery_app.task(
    name="app.tasks.indexing_tasks.check_and_resume_interrupted_indexing",
    bind=False,
)
def check_and_resume_interrupted_indexing() -> dict:
    """Check for interrupted indexing jobs and auto-resume them.

    This task runs periodically (every 2 minutes) to detect and resume
    indexing jobs that were interrupted by worker restarts or crashes.

    Returns:
        dict with resumed jobs count and details
    """
    import asyncio
    from sqlalchemy import select
    from app.models.indexing_progress import IndexingProgress, IndexingStatus
    from app.services.database import database_service

    logger.info("checking_for_interrupted_indexing_jobs")

    async def find_and_resume():
        from datetime import datetime, UTC, timedelta

        async with database_service.async_session() as session:
            # Find all users with interrupted indexing (status=IN_PROGRESS but not completed)
            result = await session.execute(
                select(IndexingProgress).where(
                    IndexingProgress.status == IndexingStatus.IN_PROGRESS,
                    IndexingProgress.processed_count < IndexingProgress.total_emails
                )
            )
            interrupted_jobs = result.scalars().all()

            # DB-BASED LOCKING: Check updated_at timestamp instead of Celery inspect
            # This prevents race conditions with solo pool where inspect.active() doesn't work
            now = datetime.now(UTC)
            cooldown_seconds = 30  # Minimum 30 seconds between resume attempts

            resumed_count = 0
            skipped_count = 0
            for job in interrupted_jobs:
                try:
                    # Check if job was updated recently (within cooldown period)
                    time_since_update = (now - job.updated_at).total_seconds()

                    if time_since_update < cooldown_seconds:
                        logger.info(
                            "skipping_resume_cooldown_active",
                            user_id=job.user_id,
                            time_since_update_sec=round(time_since_update, 1),
                            cooldown_sec=cooldown_seconds,
                            processed=job.processed_count,
                            total=job.total_emails,
                        )
                        skipped_count += 1
                        continue

                    # Trigger resume task only if cooldown passed
                    resume_user_indexing.delay(user_id=job.user_id)
                    resumed_count += 1
                    logger.info(
                        "auto_resumed_interrupted_indexing",
                        user_id=job.user_id,
                        processed=job.processed_count,
                        total=job.total_emails,
                        last_update=job.updated_at.isoformat(),
                    )
                except Exception as e:
                    logger.error(
                        "auto_resume_failed",
                        user_id=job.user_id,
                        error=str(e),
                    )

            return resumed_count, skipped_count

    # Run async code in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        resumed_count, skipped_count = loop.run_until_complete(find_and_resume())
    finally:
        loop.close()

    if resumed_count > 0 or skipped_count > 0:
        logger.info(
            "auto_resume_check_completed",
            resumed_count=resumed_count,
            skipped_count=skipped_count,
        )

    return {
        "success": True,
        "resumed_count": resumed_count,
        "skipped_count": skipped_count,
    }


@shared_task(
    bind=True,
    name="app.tasks.indexing_tasks.reindex_email_batch",
    max_retries=3,
    time_limit=600,
)
def reindex_email_batch(self, user_id: int, start_id: int, end_id: int) -> dict:
    """Reindex batch of existing emails that were received before incremental indexing was enabled.

    This task queries EmailProcessingQueue for emails in the specified ID range,
    then queues individual index_new_email_background tasks for each email.

    Args:
        self: Celery task instance
        user_id: User ID
        start_id: Start of email ID range (inclusive)
        end_id: End of email ID range (inclusive)

    Returns:
        dict with success status and count of queued emails

    Example:
        # Reindex emails 252-261 for user 3
        reindex_email_batch.delay(user_id=3, start_id=252, end_id=261)
    """
    import asyncio
    from sqlalchemy import select
    from app.models.email import EmailProcessingQueue
    from app.services.database import database_service

    logger.info(
        "reindex_batch_started",
        task_id=self.request.id,
        user_id=user_id,
        start_id=start_id,
        end_id=end_id,
    )

    async def get_emails():
        async with database_service.async_session() as session:
            result = await session.execute(
                select(EmailProcessingQueue)
                .where(
                    EmailProcessingQueue.id >= start_id,
                    EmailProcessingQueue.id <= end_id,
                    EmailProcessingQueue.user_id == user_id
                )
                .order_by(EmailProcessingQueue.id)
            )
            return result.scalars().all()

    # Get emails from database
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        emails = loop.run_until_complete(get_emails())
    finally:
        loop.close()

    logger.info(
        "reindex_batch_emails_found",
        task_id=self.request.id,
        user_id=user_id,
        count=len(emails),
    )

    # Queue individual indexing tasks
    queued_count = 0
    failed_count = 0

    for email in emails:
        try:
            # Queue background indexing task
            index_new_email_background.delay(
                user_id=email.user_id,
                message_id=email.gmail_message_id
            )
            queued_count += 1
            logger.info(
                "reindex_email_queued",
                task_id=self.request.id,
                email_id=email.id,
                subject=email.subject,
                message_id=email.gmail_message_id,
            )
        except Exception as e:
            failed_count += 1
            logger.error(
                "reindex_email_queue_failed",
                task_id=self.request.id,
                email_id=email.id,
                error=str(e),
            )

    logger.info(
        "reindex_batch_completed",
        task_id=self.request.id,
        user_id=user_id,
        queued=queued_count,
        failed=failed_count,
        total=len(emails),
    )

    return {
        "success": True,
        "user_id": user_id,
        "queued": queued_count,
        "failed": failed_count,
        "total": len(emails),
    }
