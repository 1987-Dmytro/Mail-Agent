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

        # Run async indexing in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in current thread - create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        progress = loop.run_until_complete(service.start_indexing(days_back=days_back))

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

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        progress = loop.run_until_complete(service.resume_indexing())

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

    try:
        service = EmailIndexingService(user_id=user_id)

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

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
