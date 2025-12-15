"""Email polling background tasks.

This module contains Celery tasks for polling Gmail inboxes, detecting new emails,
and queuing them for processing. Tasks run on a configurable schedule via Celery Beat.
"""

import asyncio
import os
import time
from typing import List

import structlog
from celery import shared_task
from email_validator import EmailNotValidError, validate_email
from googleapiclient.errors import HttpError
from sqlmodel import select

from app.core.gmail_client import GmailClient
from app.core.groq_client import GroqLLMClient as LLMClient
from app.core.telegram_bot import TelegramBotClient
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.services.database import database_service
from app.services.workflow_tracker import WorkflowInstanceTracker
from app.tasks.indexing_tasks import index_new_email_background

logger = structlog.get_logger(__name__)


async def _check_indexing_threshold(user_id: int, db_session) -> tuple[bool, float]:
    """Check if user's indexing is 100% complete before allowing email processing.

    This function prevents email workflow processing when RAG context is insufficient.
    Worker should NOT process emails until database is indexed 100% (COMPLETED status),
    otherwise AI responses will be incorrect and OOM crashes may occur.

    Args:
        user_id: User ID to check
        db_session: Active database session

    Returns:
        tuple[bool, float]: (is_ready, progress_percent)
            - is_ready: True ONLY if indexing status is COMPLETED, False otherwise
            - progress_percent: Current progress percentage (0-100)

    Example:
        async with database_service.async_session() as session:
            is_ready, percent = await _check_indexing_threshold(user_id, session)
            if not is_ready:
                logger.info("skipping_workflow", progress_percent=percent)
    """
    from app.models.indexing_progress import IndexingProgress, IndexingStatus

    result = await db_session.execute(
        select(IndexingProgress).where(IndexingProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        # No indexing progress record - block processing until indexing starts
        return False, 0.0

    if progress.status == IndexingStatus.COMPLETED:
        # Indexing complete - allow processing
        return True, 100.0

    # Indexing in progress or paused - calculate percentage but block processing
    if progress.total_emails == 0:
        return False, 0.0

    percent = (progress.processed_count / progress.total_emails) * 100
    # CRITICAL: Only allow processing when status is COMPLETED (not just 60% or 100%)
    # This prevents race conditions where processed_count reaches 100% before status updates
    return False, percent


@shared_task(bind=True, max_retries=3, default_retry_delay=60, time_limit=300, soft_time_limit=270)
def poll_user_emails(self, user_id: int):
    """Poll Gmail inbox for new emails for specific user.

    This task fetches unread emails from a user's Gmail inbox, extracts metadata,
    and checks for duplicates before processing. Implements retry logic for
    transient Gmail API errors.

    Args:
        self: Celery task instance (injected by bind=True)
        user_id: The ID of the user whose inbox to poll

    Raises:
        Exception: Re-raises non-retryable errors after logging
    """
    start_time = time.time()
    logger.info("polling_cycle_started", user_id=user_id)

    # Create new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Execute polling logic
        new_count, skip_count = loop.run_until_complete(_poll_user_emails_async(user_id))

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "polling_cycle_completed",
            user_id=user_id,
            new_emails=new_count,
            duplicates=skip_count,
            duration_ms=duration_ms,
        )

    except HttpError as e:
        # Handle Gmail API errors with retry logic
        status = e.resp.status
        if status in [500, 503]:
            # Transient error - retry with exponential backoff
            logger.warning(
                "gmail_transient_error_retrying",
                user_id=user_id,
                status=status,
                attempt=self.request.retries + 1,
                max_retries=self.max_retries,
            )
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        else:
            # Permanent error - log and fail
            logger.error(
                "gmail_permanent_error",
                user_id=user_id,
                status=status,
                error=str(e),
                exc_info=True,
            )
            raise

    except Exception as e:
        # Unexpected error - log with context
        logger.error(
            "polling_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise

    finally:
        # Always cleanup event loop to prevent resource leaks
        loop.close()


async def _poll_user_emails_async(user_id: int) -> tuple[int, int]:
    """Async helper for polling user emails.

    Args:
        user_id: The ID of the user whose inbox to poll

    Returns:
        tuple[int, int]: (new_emails_count, duplicates_skipped_count)
    """
    # Initialize Gmail client
    gmail_client = GmailClient(user_id)

    # Fetch unread emails from Inbox only
    emails = await gmail_client.get_messages(query="is:unread in:inbox", max_results=50)

    logger.info("emails_fetched", user_id=user_id, count=len(emails))

    # Process each email (check for duplicates, extract metadata)
    new_count = 0
    skip_count = 0

    async with database_service.async_session() as session:
        # RECOVERY: Check if indexing is complete in Pinecone but DB not updated
        # This handles edge cases where worker crashes/restarts prevented mark_complete() from running
        try:
            from app.core.vector_db_pinecone import PineconeVectorDBClient
            from app.services.indexing_recovery import IndexingRecoveryService
            import os

            pinecone_client = PineconeVectorDBClient(
                api_key=os.getenv("PINECONE_API_KEY"),
                index_name="ai-assistant-memories"
            )
            recovery_service = IndexingRecoveryService(pinecone_client)
            recovered = await recovery_service.check_and_recover_user(user_id)

            if recovered:
                logger.info(
                    "indexing_state_recovered_from_pinecone",
                    user_id=user_id,
                    note="Database synced with Pinecone reality"
                )
        except Exception as recovery_error:
            # Recovery failure shouldn't block email polling
            logger.warning(
                "indexing_recovery_failed",
                user_id=user_id,
                error=str(recovery_error)
            )

        # Check indexing progress ONCE per user (100% COMPLETED status required for workflow processing)
        # This prevents OOM crashes and incorrect AI responses due to insufficient RAG context
        indexing_ready, progress_percent = await _check_indexing_threshold(user_id, session)
        for email in emails:
            message_id = email.get("message_id")
            if not message_id:
                logger.warning("email_missing_message_id", user_id=user_id, email=email)
                continue

            # Check if email already processed (duplicate detection)
            statement = select(EmailProcessingQueue).where(
                EmailProcessingQueue.gmail_message_id == message_id
            )
            result = await session.execute(statement)
            existing_email = result.scalar_one_or_none()

            if existing_email:
                # Duplicate detected - skip
                skip_count += 1
                logger.info(
                    "duplicate_email_skipped",
                    user_id=user_id,
                    message_id=message_id,
                    existing_id=existing_email.id,
                )
                continue

            # Validate sender email format
            sender = email.get("sender", "")
            try:
                # Validate and normalize email address
                validated = validate_email(sender, check_deliverability=False)
                sender = validated.normalized
            except EmailNotValidError as e:
                logger.warning(
                    "invalid_sender_email_format",
                    user_id=user_id,
                    message_id=message_id,
                    sender=sender,
                    error=str(e),
                )
                # Use original sender even if validation fails (Gmail API should return valid emails)
                # This is a defensive measure for edge cases

            # Email is new - persist to database
            new_email = EmailProcessingQueue(
                user_id=user_id,
                gmail_message_id=message_id,
                gmail_thread_id=email.get("thread_id", ""),
                sender=sender,
                subject=email.get("subject"),
                received_at=email.get("received_at"),
                status="pending",
            )
            session.add(new_email)
            await session.flush()  # Flush to get email ID
            email_id = new_email.id  # Capture ID before commit

            # Commit email immediately - closes transaction before slow I/O
            await session.commit()
            new_count += 1

            logger.info(
                "email_persisted",
                user_id=user_id,
                email_id=email_id,
                message_id=message_id,
                sender=email.get("sender"),
                subject=email.get("subject"),
                received_at=email.get("received_at"),
            )

            # Story 2.3: Start email classification workflow
            # Workflow runs AFTER email committed - no long-lived transaction
            # Workflow will run: extract_context → classify → send_telegram → await_approval (PAUSE)

            # CRITICAL: Check if indexing is complete before starting workflow
            # This prevents OOM crashes and incorrect AI responses due to insufficient RAG context
            if not indexing_ready:
                logger.warning(
                    "workflow_skipped_indexing_incomplete",
                    email_id=email_id,
                    user_id=user_id,
                    progress_percent=round(progress_percent, 1),
                    note=f"Indexing must be 100% complete before workflow can start. Current: {progress_percent:.1f}%"
                )
                continue  # Skip workflow for this email, will be processed after indexing completes

            try:
                # Create new session for workflow (email already committed above)
                async with database_service.async_session() as workflow_session:
                    # Initialize workflow tracker with dependencies
                    llm_client = LLMClient()
                    telegram_bot_client = TelegramBotClient()
                    database_url = os.getenv("DATABASE_URL")

                    workflow_tracker = WorkflowInstanceTracker(
                        db=workflow_session,
                        gmail_client=gmail_client,
                        llm_client=llm_client,
                        telegram_bot_client=telegram_bot_client,
                        database_url=database_url,
                    )

                    # Start workflow - returns thread_id for checkpoint tracking
                    thread_id = await workflow_tracker.start_workflow(
                        email_id=email_id,
                        user_id=user_id,
                    )

                    # Commit workflow state updates (mapping, classification, status)
                    await workflow_session.commit()

                    logger.info(
                        "workflow_started",
                        email_id=email_id,
                        user_id=user_id,
                        thread_id=thread_id,
                        note="Workflow paused at await_approval, awaiting Telegram response",
                    )

                    # Index new email in vector database for RAG context retrieval
                    # This runs asynchronously in background - doesn't block workflow
                    try:
                        index_new_email_background.delay(user_id=user_id, message_id=message_id)
                        logger.info(
                            "incremental_indexing_queued",
                            email_id=email_id,
                            user_id=user_id,
                            message_id=message_id,
                        )
                    except Exception as indexing_error:
                        # Don't fail workflow if indexing fails - just log it
                        logger.warning(
                            "incremental_indexing_queue_failed",
                            email_id=email_id,
                            user_id=user_id,
                            message_id=message_id,
                            error=str(indexing_error),
                        )

            except Exception as workflow_error:
                # Log workflow initialization errors but don't fail email polling
                # Email is already saved, workflow can be retried later if needed
                logger.error(
                    "workflow_initialization_failed",
                    email_id=email_id,
                    user_id=user_id,
                    error=str(workflow_error),
                    error_type=type(workflow_error).__name__,
                    note="Email saved successfully, workflow can be retried",
                    exc_info=True,
                )

        # AUTOMATIC REPROCESSING: Check for pending emails that were blocked before indexing completed
        # This runs ONCE per polling cycle, AFTER new emails are processed
        # If indexing is now complete, we reprocess stuck pending emails
        if indexing_ready:
            # Query for pending emails (emails that were added before indexing completed)
            pending_statement = select(EmailProcessingQueue).where(
                EmailProcessingQueue.user_id == user_id,
                EmailProcessingQueue.status == "pending"
            ).order_by(EmailProcessingQueue.received_at)

            pending_result = await session.execute(pending_statement)
            pending_emails = pending_result.scalars().all()

            if pending_emails:
                logger.info(
                    "reprocessing_pending_emails",
                    user_id=user_id,
                    count=len(pending_emails),
                    note="Starting workflows for emails that were blocked before indexing completed"
                )

                reprocessed_count = 0
                for pending_email in pending_emails:
                    try:
                        # Create new session for workflow
                        async with database_service.async_session() as workflow_session:
                            # Initialize workflow tracker
                            llm_client = LLMClient()
                            telegram_bot_client = TelegramBotClient()
                            database_url = os.getenv("DATABASE_URL")

                            workflow_tracker = WorkflowInstanceTracker(
                                db=workflow_session,
                                gmail_client=gmail_client,
                                llm_client=llm_client,
                                telegram_bot_client=telegram_bot_client,
                                database_url=database_url,
                            )

                            # Start workflow
                            thread_id = await workflow_tracker.start_workflow(
                                email_id=pending_email.id,
                                user_id=user_id,
                            )

                            await workflow_session.commit()

                            logger.info(
                                "pending_email_reprocessed",
                                email_id=pending_email.id,
                                user_id=user_id,
                                thread_id=thread_id,
                                sender=pending_email.sender,
                                subject=pending_email.subject,
                            )
                            reprocessed_count += 1

                            # Queue incremental indexing if not already done
                            try:
                                index_new_email_background.delay(
                                    user_id=user_id,
                                    message_id=pending_email.gmail_message_id
                                )
                            except Exception as indexing_error:
                                logger.warning(
                                    "reprocess_indexing_queue_failed",
                                    email_id=pending_email.id,
                                    error=str(indexing_error)
                                )

                    except Exception as reprocess_error:
                        logger.error(
                            "pending_email_reprocessing_failed",
                            email_id=pending_email.id,
                            user_id=user_id,
                            error=str(reprocess_error),
                            exc_info=True,
                        )

                if reprocessed_count > 0:
                    logger.info(
                        "reprocessing_complete",
                        user_id=user_id,
                        reprocessed=reprocessed_count,
                        total_pending=len(pending_emails)
                    )

    logger.info("email_processing_summary", user_id=user_id, new_emails=new_count, duplicates=skip_count)

    return new_count, skip_count


@shared_task(time_limit=600, soft_time_limit=570)
def poll_all_users():
    """Orchestrator task to poll all active users.

    Queries the database for all active users with Gmail OAuth tokens,
    then spawns individual polling tasks for each user with a small delay
    between tasks to respect Gmail API rate limits.
    """
    logger.info("poll_all_users_started")
    start_time = time.time()

    # Create new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Run async database query in event loop
        users = loop.run_until_complete(_get_active_users())

        logger.info("active_users_found", count=len(users))

        # Queue individual polling tasks for each user
        queued_count = 0
        for user in users:
            if user.gmail_oauth_token:
                # Queue individual polling task
                poll_user_emails.delay(user.id)
                queued_count += 1
                # Add small delay to avoid rate limit spikes
                time.sleep(1)
            else:
                logger.debug("user_missing_gmail_token", user_id=user.id, email=user.email)

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "poll_all_users_completed",
            total_users=len(users),
            users_queued=queued_count,
            users_skipped=len(users) - queued_count,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(
            "poll_all_users_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise

    finally:
        # Always cleanup event loop to prevent resource leaks
        loop.close()


async def _get_active_users() -> List[User]:
    """Query database for all active users with Gmail tokens.

    Returns:
        List[User]: List of active users
    """
    async with database_service.async_session() as session:
        statement = select(User).where(User.is_active == True)  # noqa: E712
        result = await session.execute(statement)
        users = result.scalars().all()
        return list(users)
