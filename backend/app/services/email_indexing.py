"""Email History Indexing Service for Mail Agent.

This module provides email history indexing functionality for the RAG system,
enabling context-aware email response generation by indexing user's Gmail history
into ChromaDB vector database.

Key Features:
- 90-day lookback strategy (fast onboarding in <10 minutes)
- Batch processing with rate limiting (50 emails/batch, 60s intervals)
- Checkpoint mechanism for resumable indexing after interruption
- Progress tracking via IndexingProgress database table
- Incremental indexing for new emails after initial sync
- Error handling with exponential backoff retry logic
- Telegram notification on completion

Usage:
    service = EmailIndexingService(user_id=123)

    # Start initial indexing
    progress = await service.start_indexing(days_back=90)

    # Resume interrupted job
    progress = await service.resume_indexing()

    # Index single new email (incremental)
    success = await service.index_new_email(message_id="abc123")

Reference: docs/tech-spec-epic-3.md#Email-History-Indexing-Strategy
"""

import asyncio
import os
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional

import structlog
from langdetect import detect, LangDetectException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.embedding_service import EmbeddingService
from app.core.gmail_client import GmailClient
from app.core.preprocessing import extract_email_text, strip_html, truncate_to_tokens
from app.core.telegram_bot import TelegramBotClient
from app.core.vector_db_pinecone import PineconeVectorDBClient
from app.models.indexing_progress import IndexingProgress, IndexingStatus
from app.models.user import User
from app.services.database import DatabaseService, database_service
from app.utils.errors import GmailAPIError, GeminiAPIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


class EmailIndexingService:
    """Service for indexing user's email history into vector database.

    This service orchestrates the email history indexing workflow:
    1. Retrieve emails from Gmail API (90-day lookback with pagination)
    2. Extract metadata (message_id, thread_id, sender, date, subject, language, snippet)
    3. Generate embeddings via EmbeddingService (batch of 50)
    4. Store embeddings + metadata in ChromaDB via VectorDBClient
    5. Update progress tracking in IndexingProgress table
    6. Send Telegram notification on completion

    Attributes:
        user_id: Database ID of user
        db_service: Database service for IndexingProgress queries
        gmail_client: Gmail API client wrapper
        embedding_service: Gemini embedding service
        vector_db_client: ChromaDB client
        telegram_bot: Telegram bot for notifications
        logger: Structured logger
    """

    # Batch processing constants
    GMAIL_PAGE_SIZE = 100  # Max messages per Gmail API page
    EMBEDDING_BATCH_SIZE = 50  # Max emails per embedding batch (rate limit)
    RATE_LIMIT_DELAY_SECONDS = 60  # Delay between batches (50 emails/min)

    # Error handling constants
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Exponential backoff: 2s, 4s, 8s
    MAX_RETRY_COUNT = 3  # Maximum retry attempts for failed indexing jobs

    def __init__(
        self,
        user_id: int,
        db_service: DatabaseService = None,
        gmail_client: GmailClient = None,
        embedding_service: EmbeddingService = None,
        vector_db_client: PineconeVectorDBClient = None,
        telegram_bot: TelegramBotClient = None,
    ):
        """Initialize email indexing service for specific user.

        Args:
            user_id: Database ID of user
            db_service: Optional DatabaseService for dependency injection (testing)
            gmail_client: Optional GmailClient for dependency injection (testing)
            embedding_service: Optional EmbeddingService for dependency injection (testing)
            vector_db_client: Optional PineconeVectorDBClient for dependency injection (testing)
            telegram_bot: Optional TelegramBotClient for dependency injection (testing)

        Example:
            # Production usage
            service = EmailIndexingService(user_id=123)

            # Test usage with mocks
            service = EmailIndexingService(
                user_id=123,
                gmail_client=mock_gmail,
                embedding_service=mock_embeddings
            )
        """
        self.user_id = user_id
        self.db_service = db_service or database_service
        self.gmail_client = gmail_client or GmailClient(user_id=user_id, db_service=self.db_service)
        self.embedding_service = embedding_service or EmbeddingService()
        # Use Pinecone for cloud-native persistent storage
        from app.core.config import settings
        self.vector_db_client = vector_db_client or PineconeVectorDBClient(
            api_key=settings.PINECONE_API_KEY,
            index_name="ai-assistant-memories"
        )
        self.telegram_bot = telegram_bot or TelegramBotClient()
        self.logger = structlog.get_logger(__name__)

        self.logger.info(
            "email_indexing_service_initialized",
            user_id=user_id,
            gmail_page_size=self.GMAIL_PAGE_SIZE,
            batch_size=self.EMBEDDING_BATCH_SIZE,
        )

    async def start_indexing(self, days_back: int = 90) -> IndexingProgress:
        """Start new email history indexing job for user.

        Workflow:
        1. Check if indexing job already exists (prevent duplicates)
        2. Calculate 90-day cutoff date
        3. Retrieve total email count from Gmail (estimate via pagination)
        4. Create IndexingProgress record with status=in_progress
        5. Process emails in batches (50 per batch with 60s intervals)
        6. Update progress after each batch
        7. Mark complete and send Telegram notification

        Args:
            days_back: Number of days to look back (default: 90)

        Returns:
            IndexingProgress record with initial status

        Raises:
            ValueError: If indexing job already exists for user
            GmailAPIError: If Gmail API fails

        Example:
            progress = await service.start_indexing(days_back=90)
            print(f"Indexing started: {progress.total_emails} emails to process")
        """
        # Check for existing indexing job
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(
                    IndexingProgress.user_id == self.user_id,
                    IndexingProgress.status.in_([IndexingStatus.IN_PROGRESS, IndexingStatus.PAUSED])
                )
            )
            existing_progress = result.scalar_one_or_none()

            if existing_progress:
                raise ValueError(
                    f"Indexing job already exists for user {self.user_id} "
                    f"(status: {existing_progress.status}). Use resume_indexing() instead."
                )

        self.logger.info("indexing_started", user_id=self.user_id, days_back=days_back)

        # Create IndexingProgress record IMMEDIATELY to prevent duplicate tasks
        # We'll update total_emails after Gmail retrieval completes
        async with self.db_service.async_session() as session:
            progress = IndexingProgress(
                user_id=self.user_id,
                total_emails=0,  # Will be updated after Gmail retrieval
                processed_count=0,
                status=IndexingStatus.IN_PROGRESS,
            )
            session.add(progress)
            await session.commit()
            await session.refresh(progress)

        self.logger.info(
            "indexing_progress_record_created",
            user_id=self.user_id,
            progress_id=progress.id,
        )

        # Retrieve emails from Gmail (progressively updates total_emails during fetch)
        emails = await self.retrieve_gmail_emails(days_back=days_back, progress_id=progress.id)
        total_emails = len(emails)

        self.logger.info(
            "gmail_emails_retrieved",
            user_id=self.user_id,
            total_emails=total_emails,
            days_back=days_back,
        )

        # Verify final total_emails count matches (should already be set by progressive updates)
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.id == progress.id)
            )
            progress = result.scalar_one()
            # Final verification - should match unless some messages failed to fetch
            if progress.total_emails != total_emails:
                self.logger.warning(
                    "gmail_total_mismatch",
                    user_id=self.user_id,
                    progressive_total=progress.total_emails,
                    final_total=total_emails,
                )
                progress.total_emails = total_emails
                await session.commit()
            await session.refresh(progress)

        # Process emails in batches
        try:
            for i in range(0, total_emails, self.EMBEDDING_BATCH_SIZE):
                batch = emails[i : i + self.EMBEDDING_BATCH_SIZE]
                batch_number = (i // self.EMBEDDING_BATCH_SIZE) + 1
                total_batches = (total_emails + self.EMBEDDING_BATCH_SIZE - 1) // self.EMBEDDING_BATCH_SIZE

                self.logger.info(
                    "processing_batch",
                    user_id=self.user_id,
                    batch_number=batch_number,
                    total_batches=total_batches,
                    batch_size=len(batch),
                )

                # Process batch (embed + store)
                processed_count = await self.process_batch(batch)

                # Update progress with checkpoint
                last_message_id = batch[-1]["message_id"] if batch else None
                await self.update_progress(
                    processed_count=i + processed_count,
                    last_message_id=last_message_id,
                )

                # Rate limiting: sleep between batches (except last batch)
                if i + self.EMBEDDING_BATCH_SIZE < total_emails:
                    self.logger.info(
                        "rate_limit_delay",
                        user_id=self.user_id,
                        delay_seconds=self.RATE_LIMIT_DELAY_SECONDS,
                        reason="Gemini API rate limit (50 requests/min)",
                    )
                    await asyncio.sleep(self.RATE_LIMIT_DELAY_SECONDS)

            # Mark indexing complete
            await self.mark_complete()

            # Send Telegram notification
            await self._send_completion_notification(total_emails)

            self.logger.info(
                "indexing_completed",
                user_id=self.user_id,
                total_emails=total_emails,
            )

            # Return final progress record
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
                )
                return result.scalar_one()

        except Exception as e:
            # Handle errors and update progress status
            await self.handle_error(e)
            raise

    async def retrieve_gmail_emails(
        self,
        days_back: int = 90,
        page_token: Optional[str] = None,
        progress_id: Optional[int] = None,
    ) -> List[Dict]:
        """Retrieve emails from Gmail API with 90-day filtering and pagination.

        Implements Gmail pagination to handle large mailboxes:
        - Retrieve in batches of 100 messages (GMAIL_PAGE_SIZE)
        - Use nextPageToken for pagination
        - Filter by date: after:{90_days_ago_unix_timestamp}
        - Continue until no more pages or cutoff date reached
        - Progressively updates total_emails in IndexingProgress for UX feedback

        Args:
            days_back: Number of days to look back (default: 90)
            page_token: Optional pagination token for resuming
            progress_id: Optional IndexingProgress ID for progressive total_emails updates

        Returns:
            List of email dicts with full message details:
            - message_id: Gmail message ID
            - thread_id: Gmail thread ID
            - sender: From header
            - subject: Subject line
            - date: Internal date
            - body: Email body text
            - snippet: First 200 chars preview

        Raises:
            GmailAPIError: If Gmail API fails

        Example:
            emails = await service.retrieve_gmail_emails(days_back=90, progress_id=progress.id)
            # Returns: [{message_id: "abc", thread_id: "xyz", ...}, ...]
        """
        # Calculate cutoff date (90 days ago)
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
        cutoff_timestamp = int(cutoff_date.timestamp())

        # Build Gmail query with date filter
        query = f"after:{cutoff_timestamp}"

        self.logger.info(
            "gmail_retrieval_started",
            user_id=self.user_id,
            days_back=days_back,
            cutoff_date=cutoff_date.isoformat(),
            query=query,
        )

        all_emails = []
        current_page_token = page_token
        page_count = 0

        # Pagination loop
        while True:
            page_count += 1

            # Get page of message IDs
            service = await self.gmail_client._get_gmail_service()

            list_params = {
                "userId": "me",
                "q": query,
                "maxResults": self.GMAIL_PAGE_SIZE,
            }
            if current_page_token:
                list_params["pageToken"] = current_page_token

            try:
                list_result = service.users().messages().list(**list_params).execute()
            except Exception as e:
                raise GmailAPIError(f"Failed to list messages: {str(e)}") from e

            messages = list_result.get("messages", [])

            if not messages:
                # No more messages
                break

            self.logger.info(
                "gmail_page_retrieved",
                user_id=self.user_id,
                page_count=page_count,
                messages_in_page=len(messages),
            )

            # Progressively update total_emails for UX feedback (if progress_id provided)
            if progress_id:
                try:
                    async with self.db_service.async_session() as session:
                        result = await session.execute(
                            select(IndexingProgress).where(IndexingProgress.id == progress_id)
                        )
                        progress = result.scalar_one_or_none()
                        if progress:
                            # Increment total_emails by actual messages in this page
                            progress.total_emails += len(messages)
                            await session.commit()

                            self.logger.debug(
                                "gmail_progress_updated",
                                user_id=self.user_id,
                                page_count=page_count,
                                total_emails_so_far=progress.total_emails,
                            )
                except Exception as e:
                    # Don't fail retrieval if progress update fails
                    self.logger.warning(
                        "gmail_progress_update_failed",
                        user_id=self.user_id,
                        error=str(e),
                    )

            # Fetch full details for each message in page
            for msg in messages:
                try:
                    message_detail = service.users().messages().get(
                        userId="me",
                        id=msg["id"],
                        format="full",
                    ).execute()

                    # Extract email data
                    email_data = await self._parse_gmail_message(message_detail)
                    all_emails.append(email_data)

                except Exception as e:
                    self.logger.warning(
                        "failed_to_fetch_message_detail",
                        user_id=self.user_id,
                        message_id=msg["id"],
                        error=str(e),
                    )
                    # Continue with other messages
                    continue

            # Check for next page
            current_page_token = list_result.get("nextPageToken")
            if not current_page_token:
                # No more pages
                break

        self.logger.info(
            "gmail_retrieval_completed",
            user_id=self.user_id,
            total_emails=len(all_emails),
            pages_fetched=page_count,
        )

        return all_emails

    async def _parse_gmail_message(self, message: Dict) -> Dict:
        """Parse Gmail API message into standardized format.

        Args:
            message: Gmail API message object (format=full)

        Returns:
            Dict with keys: message_id, thread_id, sender, subject, date, body, snippet
        """
        # Extract headers
        headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}

        # Extract body using GmailClient's method
        body = self.gmail_client._extract_body(message["payload"])

        # Parse date
        internal_date = message.get("internalDate")
        date = self.gmail_client._parse_gmail_date(internal_date) if internal_date else datetime.now(UTC)

        return {
            "message_id": message["id"],
            "thread_id": message["threadId"],
            "sender": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": date,
            "body": body,
            "snippet": message.get("snippet", ""),
        }

    async def process_batch(self, emails: List[Dict]) -> int:
        """Process batch of emails: embed and store in vector database.

        Workflow for each email in batch:
        1. Preprocess email body (strip HTML, truncate to 2048 tokens)
        2. Extract metadata (message_id, thread_id, sender, date, subject, language, snippet)
        3. Generate embeddings via EmbeddingService.embed_batch()
        4. Store embeddings + metadata in ChromaDB via VectorDBClient.insert_embeddings_batch()

        Args:
            emails: List of email dicts from retrieve_gmail_emails()

        Returns:
            Number of emails successfully processed

        Raises:
            GeminiAPIError: If embedding generation fails
            Exception: If ChromaDB storage fails

        Example:
            processed = await service.process_batch(emails[0:50])
            # Returns: 50 (all emails processed successfully)
        """
        if not emails:
            return 0

        self.logger.info(
            "batch_processing_started",
            user_id=self.user_id,
            batch_size=len(emails),
        )

        # Preprocess email bodies
        preprocessed_bodies = []
        for email in emails:
            body = email["body"]
            # Strip HTML and truncate
            preprocessed = truncate_to_tokens(strip_html(body), max_tokens=2048)
            preprocessed_bodies.append(preprocessed)

        # Generate embeddings (batch call)
        try:
            embeddings = self.embedding_service.embed_batch(
                texts=preprocessed_bodies,
                batch_size=self.EMBEDDING_BATCH_SIZE,
            )
        except Exception as e:
            raise GeminiAPIError(f"Failed to generate embeddings: {str(e)}") from e

        # Extract metadata and ids for each email
        metadatas = []
        ids = []
        for email in emails:
            metadata = self._extract_metadata(email)
            metadatas.append(metadata)
            ids.append(email["message_id"])  # Use Gmail message_id as unique identifier

        # Store in ChromaDB
        try:
            self.vector_db_client.insert_embeddings_batch(
                collection_name="email_embeddings",
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            # Note: insert_embeddings_batch returns None on success, raises exception on failure

        except Exception as e:
            self.logger.error(
                "chromadb_insertion_failed",
                user_id=self.user_id,
                batch_size=len(emails),
                error=str(e),
            )
            raise

        self.logger.info(
            "batch_processing_completed",
            user_id=self.user_id,
            processed_count=len(emails),
        )

        return len(emails)

    def _extract_metadata(self, email: Dict) -> Dict:
        """Extract metadata from email for ChromaDB storage.

        Metadata schema (AC #5, #6):
        - user_id: User ID (required for multi-tenant filtering)
        - message_id: Gmail message ID (unique identifier)
        - thread_id: Gmail thread ID (preserve thread relationships)
        - sender: From header (email address)
        - date: Email date in ISO format (YYYY-MM-DD)
        - subject: Subject line
        - language: Detected language code (en/ru/de/uk/etc)
        - snippet: First 200 characters of email body

        Args:
            email: Email dict from retrieve_gmail_emails()

        Returns:
            Dict with metadata fields matching ChromaDB collection schema

        Example:
            metadata = service._extract_metadata(email)
            # Returns: {
            #     "message_id": "abc123",
            #     "thread_id": "xyz789",
            #     "sender": "user@example.com",
            #     "date": "2025-11-09",
            #     "subject": "Meeting reminder",
            #     "language": "en",
            #     "snippet": "Just a quick reminder about..."
            # }
        """
        # Detect language from body
        language = "en"  # Default fallback
        try:
            body = email.get("body", "")
            if body and len(body.strip()) > 10:
                language = detect(body)
        except LangDetectException:
            # Detection failed - use default
            pass

        # Extract snippet (first 200 chars of body)
        body = email.get("body", "")
        snippet = body[:200] if len(body) > 200 else body

        # Format date as ISO string (YYYY-MM-DD) and extract timestamp
        date = email.get("date", datetime.now(UTC))
        if isinstance(date, datetime):
            date_str = date.strftime("%Y-%m-%d")
            # Store Unix timestamp for temporal filtering (seconds since epoch)
            # This enables "last 7 days" filtering in semantic search
            timestamp = int(date.timestamp())
        else:
            date_str = str(date)
            timestamp = int(datetime.now(UTC).timestamp())

        metadata = {
            "user_id": str(self.user_id),  # Required for multi-tenant filtering in semantic search
            "message_id": email["message_id"],
            "thread_id": email["thread_id"],
            "sender": email["sender"],
            "date": date_str,  # Human-readable date (YYYY-MM-DD)
            "timestamp": timestamp,  # Unix timestamp for temporal filtering
            "subject": email.get("subject", ""),
            "language": language,
            "snippet": snippet,
        }

        return metadata

    async def update_progress(
        self,
        processed_count: int,
        last_message_id: Optional[str] = None,
    ) -> None:
        """Update indexing progress with checkpoint for resumption.

        Updates IndexingProgress record:
        - processed_count: Total emails processed so far
        - last_processed_message_id: Checkpoint for resumption

        Args:
            processed_count: Total emails processed
            last_message_id: Last processed Gmail message ID (checkpoint)

        Example:
            await service.update_progress(processed_count=50, last_message_id="abc123")
        """
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
            )
            progress = result.scalar_one()

            progress.processed_count = processed_count
            if last_message_id:
                progress.last_processed_message_id = last_message_id

            await session.commit()

        self.logger.info(
            "progress_updated",
            user_id=self.user_id,
            processed_count=processed_count,
            last_message_id=last_message_id,
        )

    async def resume_indexing(self) -> Optional[IndexingProgress]:
        """Resume interrupted email indexing job from checkpoint.

        Workflow:
        1. Check for existing indexing job with status=in_progress or paused
        2. Find last_processed_message_id (checkpoint)
        3. Retrieve remaining emails from Gmail (skip already processed)
        4. Continue batch processing from checkpoint
        5. Mark complete when all emails processed

        Returns:
            IndexingProgress record if resumption successful, None if no job to resume

        Raises:
            ValueError: If no interrupted job found

        Example:
            progress = await service.resume_indexing()
            if progress:
                print(f"Resumed from {progress.processed_count}/{progress.total_emails}")
        """
        # Find interrupted job
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(
                    IndexingProgress.user_id == self.user_id,
                    IndexingProgress.status.in_([IndexingStatus.IN_PROGRESS, IndexingStatus.PAUSED])
                )
            )
            progress = result.scalar_one_or_none()

            if not progress:
                raise ValueError(f"No interrupted indexing job found for user {self.user_id}")

            # Check retry_after timestamp for paused jobs
            if progress.retry_after:
                now = datetime.now(UTC)
                self.logger.debug(
                    "retry_after_check",
                    user_id=self.user_id,
                    retry_after=progress.retry_after.isoformat() if progress.retry_after else None,
                    now=now.isoformat(),
                    will_block=now < progress.retry_after,
                )
                if now < progress.retry_after:
                    time_remaining = (progress.retry_after - now).total_seconds() / 60
                    raise ValueError(
                        f"Cannot resume indexing yet. Retry allowed after {progress.retry_after.isoformat()} "
                        f"({time_remaining:.1f} minutes remaining)"
                    )
                self.logger.info(
                    "retry_after_passed",
                    user_id=self.user_id,
                    retry_after=progress.retry_after.isoformat(),
                    retry_count=progress.retry_count,
                )

            # Check if already completed
            if progress.processed_count >= progress.total_emails:
                self.logger.info(
                    "indexing_already_complete",
                    user_id=self.user_id,
                    processed=progress.processed_count,
                    total=progress.total_emails,
                )
                await self.mark_complete()
                return progress

        self.logger.info(
            "indexing_resumed",
            user_id=self.user_id,
            processed=progress.processed_count,
            total=progress.total_emails,
            checkpoint=progress.last_processed_message_id,
        )

        # Retrieve remaining emails (simplified - in production would use checkpoint)
        # For now, retrieve all and skip already processed
        all_emails = await self.retrieve_gmail_emails(days_back=90)

        # Filter to only unprocessed emails
        # (In production, would use last_processed_message_id to query Gmail efficiently)
        remaining_emails = all_emails[progress.processed_count :]

        # Process remaining batches
        for i in range(0, len(remaining_emails), self.EMBEDDING_BATCH_SIZE):
            batch = remaining_emails[i : i + self.EMBEDDING_BATCH_SIZE]

            # Process batch
            processed_count = await self.process_batch(batch)

            # Update progress
            total_processed = progress.processed_count + i + processed_count
            last_message_id = batch[-1]["message_id"] if batch else None
            await self.update_progress(
                processed_count=total_processed,
                last_message_id=last_message_id,
            )

            # Rate limiting
            if i + self.EMBEDDING_BATCH_SIZE < len(remaining_emails):
                await asyncio.sleep(self.RATE_LIMIT_DELAY_SECONDS)

        # Mark complete
        await self.mark_complete()

        # Send notification
        await self._send_completion_notification(progress.total_emails)

        # Return final progress
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
            )
            return result.scalar_one()

    async def mark_complete(self) -> None:
        """Mark indexing job as completed.

        Updates IndexingProgress:
        - status = completed
        - completed_at = current timestamp

        Example:
            await service.mark_complete()
        """
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
            )
            progress = result.scalar_one()

            progress.status = IndexingStatus.COMPLETED
            progress.completed_at = datetime.now(UTC)

            await session.commit()

        self.logger.info("indexing_marked_complete", user_id=self.user_id)

    async def handle_error(self, error: Exception) -> None:
        """Handle indexing errors and update progress status with retry logic.

        Error handling strategy with retry:
        - Check retry_count < MAX_RETRY_COUNT (3)
        - If retry available:
          - Increment retry_count
          - Set retry_after = now + (2 ^ retry_count) minutes (exponential backoff)
          - Set status = PAUSED (will be auto-resumed after retry_after)
        - If max retries exceeded:
          - Set status = FAILED (permanent failure)
        - Preserve partial progress (do not rollback)

        Exponential backoff schedule:
        - Retry 1: 2 minutes
        - Retry 2: 4 minutes
        - Retry 3: 8 minutes
        - After retry 3: FAILED

        Args:
            error: The exception that occurred

        Example:
            try:
                await service.start_indexing()
            except Exception as e:
                await service.handle_error(e)
        """
        self.logger.error(
            "indexing_error",
            user_id=self.user_id,
            error_type=type(error).__name__,
            error_message=str(error),
        )

        # Update progress with retry logic
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
            )
            progress = result.scalar_one_or_none()

            if progress:
                # Check if retries available
                if progress.retry_count < self.MAX_RETRY_COUNT:
                    # Increment retry count
                    progress.retry_count += 1

                    # Calculate exponential backoff: 2^retry_count minutes
                    backoff_minutes = 2 ** progress.retry_count
                    progress.retry_after = datetime.now(UTC) + timedelta(minutes=backoff_minutes)

                    # Set status to PAUSED (will be resumed after retry_after)
                    progress.status = IndexingStatus.PAUSED
                    progress.error_message = f"{type(error).__name__}: {str(error)} (Retry {progress.retry_count}/{self.MAX_RETRY_COUNT})"

                    self.logger.info(
                        "indexing_paused_for_retry",
                        user_id=self.user_id,
                        retry_count=progress.retry_count,
                        retry_after=progress.retry_after.isoformat(),
                        backoff_minutes=backoff_minutes,
                    )
                else:
                    # Max retries exceeded - mark as permanently failed
                    progress.status = IndexingStatus.FAILED
                    progress.error_message = f"{type(error).__name__}: {str(error)} (Max retries {self.MAX_RETRY_COUNT} exceeded)"

                    self.logger.error(
                        "indexing_failed_max_retries",
                        user_id=self.user_id,
                        retry_count=progress.retry_count,
                        error_message=progress.error_message,
                    )

                await session.commit()

    async def index_new_email(self, message_id: str) -> bool:
        """Index single new email for incremental indexing.

        Called by email polling service (Story 1.6) when new email detected.
        Only processes if initial indexing is complete.

        Workflow:
        1. Check if initial indexing complete (status=completed)
        2. If incomplete, skip (wait for initial sync)
        3. If complete, fetch email from Gmail
        4. Preprocess, embed, and store immediately (no batch delay)
        5. Log incremental indexing event

        Args:
            message_id: Gmail message ID of new email

        Returns:
            True if indexed successfully, False if skipped or failed

        Example:
            # Called by email polling service
            success = await service.index_new_email(message_id="abc123")
        """
        # Check if initial indexing complete
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
            )
            progress = result.scalar_one_or_none()

            if not progress or progress.status != IndexingStatus.COMPLETED:
                self.logger.info(
                    "incremental_indexing_skipped",
                    user_id=self.user_id,
                    message_id=message_id,
                    reason="Initial indexing not complete",
                )
                return False

        try:
            # Fetch email from Gmail
            service = await self.gmail_client._get_gmail_service()
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()

            email_data = await self._parse_gmail_message(message)

            # Process single email (no batch delay)
            processed = await self.process_batch([email_data])

            if processed == 1:
                self.logger.info(
                    "incremental_indexing_success",
                    user_id=self.user_id,
                    message_id=message_id,
                )
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(
                "incremental_indexing_failed",
                user_id=self.user_id,
                message_id=message_id,
                error=str(e),
            )
            return False

    async def _send_completion_notification(self, total_emails: int) -> None:
        """Send Telegram notification when indexing completes.

        Message format (AC #10):
        "✅ Email indexing complete! {processed_count} emails indexed from the last 90 days.
        Completed in {duration_minutes} minutes."

        Args:
            total_emails: Total number of emails indexed

        Example:
            await service._send_completion_notification(total_emails=437)
        """
        # Get user's telegram_id
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(User).where(User.id == self.user_id)
            )
            user = result.scalar_one_or_none()

            if not user or not user.telegram_id:
                self.logger.warning(
                    "telegram_notification_skipped",
                    user_id=self.user_id,
                    reason="User has no telegram_id",
                )
                return

            # Get indexing progress for duration calculation
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == self.user_id)
            )
            progress = result.scalar_one()

            # Calculate duration
            if progress.created_at and progress.completed_at:
                duration = progress.completed_at - progress.created_at
                duration_minutes = int(duration.total_seconds() / 60)
            else:
                duration_minutes = 0

        # Format notification message
        message = (
            f"✅ Email indexing complete! {total_emails} emails indexed from the last 90 days.\n"
            f"Completed in {duration_minutes} minutes."
        )

        # Send with retry logic
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                await self.telegram_bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=message,
                )
                self.logger.info(
                    "telegram_notification_sent",
                    user_id=self.user_id,
                    telegram_id=user.telegram_id,
                )
                break
            except Exception as e:
                self.logger.warning(
                    "telegram_notification_failed",
                    user_id=self.user_id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(e),
                )
                if attempt < max_attempts:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def cleanup_old_emails(self, days: int = 90) -> int:
        """Remove emails older than N days from vector database.

        Implements 90-day retention policy for vector embeddings (2025 best practice).
        Reduces storage costs and improves query performance by removing stale data.

        Args:
            days: Maximum age of emails to keep (default: 90 days)

        Returns:
            Number of emails deleted from vector DB

        Example:
            deleted_count = await service.cleanup_old_emails(days=90)
            print(f"Cleaned up {deleted_count} old emails")
        """
        from datetime import datetime, timedelta, UTC

        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        cutoff_timestamp = int(cutoff_date.timestamp())

        self.logger.info(
            "cleanup_old_emails_started",
            user_id=self.user_id,
            days=days,
            cutoff_date=cutoff_date.isoformat()
        )

        try:
            # Get ChromaDB collection
            collection = self.vector_db_client.get_collection("email_embeddings")

            # Query for old emails to delete
            old_emails = collection.get(
                where={
                    "$and": [
                        {"user_id": str(self.user_id)},
                        {"timestamp": {"$lt": cutoff_timestamp}}
                    ]
                },
                include=["metadatas"]
            )

            deleted_count = 0
            if old_emails and old_emails.get('ids'):
                deleted_count = len(old_emails['ids'])

                # Delete old emails
                collection.delete(ids=old_emails['ids'])

                self.logger.info(
                    "cleanup_old_emails_completed",
                    user_id=self.user_id,
                    deleted_count=deleted_count,
                    cutoff_date=cutoff_date.isoformat()
                )
            else:
                self.logger.info(
                    "cleanup_old_emails_no_emails_to_delete",
                    user_id=self.user_id,
                    cutoff_date=cutoff_date.isoformat()
                )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "cleanup_old_emails_failed",
                user_id=self.user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
