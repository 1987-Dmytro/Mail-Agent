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
from app.core.llm_client import LLMClient
from app.core.telegram_bot import TelegramBotClient
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.services.database import database_service
from app.services.workflow_tracker import WorkflowInstanceTracker

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
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

    try:
        # Run async operations in event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

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


async def _poll_user_emails_async(user_id: int) -> tuple[int, int]:
    """Async helper for polling user emails.

    Args:
        user_id: The ID of the user whose inbox to poll

    Returns:
        tuple[int, int]: (new_emails_count, duplicates_skipped_count)
    """
    # Initialize Gmail client
    gmail_client = GmailClient(user_id)

    # Fetch unread emails
    emails = await gmail_client.get_messages(query="is:unread", max_results=50)

    logger.info("emails_fetched", user_id=user_id, count=len(emails))

    # Process each email (check for duplicates, extract metadata)
    new_count = 0
    skip_count = 0

    async with database_service.async_session() as session:
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
            await session.flush()  # Flush to get email ID before commit
            new_count += 1

            logger.info(
                "email_persisted",
                user_id=user_id,
                email_id=new_email.id,
                message_id=message_id,
                sender=email.get("sender"),
                subject=email.get("subject"),
                received_at=email.get("received_at"),
            )

            # Story 2.3: Start email classification workflow
            # Workflow will run: extract_context → classify → send_telegram → await_approval (PAUSE)
            try:
                # Initialize workflow tracker with dependencies
                llm_client = LLMClient()
                telegram_bot_client = TelegramBotClient()
                database_url = os.getenv("DATABASE_URL")

                workflow_tracker = WorkflowInstanceTracker(
                    db=session,
                    gmail_client=gmail_client,
                    llm_client=llm_client,
                    telegram_bot_client=telegram_bot_client,
                    database_url=database_url,
                )

                # Start workflow - returns thread_id for checkpoint tracking
                thread_id = await workflow_tracker.start_workflow(
                    email_id=new_email.id,
                    user_id=user_id,
                )

                logger.info(
                    "workflow_started",
                    email_id=new_email.id,
                    user_id=user_id,
                    thread_id=thread_id,
                    note="Workflow paused at await_approval, awaiting Telegram response",
                )

            except Exception as workflow_error:
                # Log workflow initialization errors but don't fail email polling
                # Email is already saved, workflow can be retried later if needed
                logger.error(
                    "workflow_initialization_failed",
                    email_id=new_email.id,
                    user_id=user_id,
                    error=str(workflow_error),
                    error_type=type(workflow_error).__name__,
                    note="Email saved successfully, workflow can be retried",
                    exc_info=True,
                )

        # Commit all new emails in batch
        await session.commit()

    logger.info("email_processing_summary", user_id=user_id, new_emails=new_count, duplicates=skip_count)

    return new_count, skip_count


@shared_task
def poll_all_users():
    """Orchestrator task to poll all active users.

    Queries the database for all active users with Gmail OAuth tokens,
    then spawns individual polling tasks for each user with a small delay
    between tasks to respect Gmail API rate limits.
    """
    logger.info("poll_all_users_started")
    start_time = time.time()

    try:
        # Run async database query in event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

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
