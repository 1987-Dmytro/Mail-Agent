"""
Response Sending Service

This service handles sending AI-generated response drafts via Gmail API
and indexing sent responses into ChromaDB for future RAG context.

Integrates with:
- GmailClient (Story 1.9): Sends emails with threading support
- TelegramBotClient (Epic 2): Sends confirmation messages
- EmbeddingService (Story 3.2): Generates embeddings for sent responses
- VectorDBClient (Story 3.1): Stores embeddings in ChromaDB
- EmailProcessingQueue (Epic 1-3): Updates status after sending
- WorkflowMapping (Story 2.6): Updates workflow state

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.9 (Response Editing and Sending)
"""

import structlog
from datetime import datetime, UTC
from typing import Optional
from sqlmodel import Session, select
from telegram import Update
from telegram.ext import ContextTypes

from app.core.gmail_client import GmailClient
from app.core.telegram_bot import TelegramBotClient
from app.core.embedding_service import EmbeddingService
from app.core.vector_db_pinecone import PineconeVectorDBClient
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User
from app.services.database import DatabaseService, database_service

logger = structlog.get_logger(__name__)


class ResponseSendingService:
    """Service for sending AI-generated response drafts and indexing sent responses.

    This service implements the send workflow (AC #4-9):
    1. User clicks [Send] button on response draft message
    2. Load response_draft from EmailProcessingQueue (works for both original and edited drafts)
    3. Send email via GmailClient with proper threading (In-Reply-To headers)
    4. Update EmailProcessingQueue.status to "completed"
    5. Send Telegram confirmation: "✅ Response sent to {sender}"
    6. Generate embedding for sent response
    7. Index sent response into ChromaDB vector database

    This service also implements reject workflow:
    1. User clicks [Reject] button
    2. Update EmailProcessingQueue.status to "rejected"
    3. Send Telegram confirmation

    Attributes:
        telegram_bot: TelegramBotClient instance for confirmation messages
        embedding_service: EmbeddingService for generating embeddings
        vector_db_client: VectorDBClient for storing embeddings
        db_service: DatabaseService for creating database sessions
        logger: Structured logger
    """

    def __init__(
        self,
        telegram_bot: TelegramBotClient,
        embedding_service: EmbeddingService,
        vector_db_client: PineconeVectorDBClient,
        db_service: DatabaseService = None
    ):
        """Initialize response sending service.

        Args:
            telegram_bot: Initialized TelegramBotClient instance
            embedding_service: EmbeddingService for generating embeddings
            vector_db_client: PineconeVectorDBClient for storing embeddings in Pinecone
            db_service: DatabaseService for creating database sessions (defaults to global instance)
        """
        self.telegram_bot = telegram_bot
        self.embedding_service = embedding_service
        self.vector_db_client = vector_db_client
        self.db_service = db_service or database_service
        self.logger = logger.bind(service="response_sending")

    async def handle_send_response_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        email_id: int,
        user_id: int
    ) -> None:
        """Handle Send button callback - send response via Gmail (AC #4-8).

        Workflow:
        1. Parse callback_data to extract email_id
        2. Load EmailProcessingQueue with draft_response field
        3. Verify draft_response is not empty (works for both original and edited - AC #4)
        4. Load original email metadata (sender, subject, gmail_thread_id)
        5. Send email via GmailClient.send_email() with threading (AC #5, #6)
        6. Update EmailProcessingQueue.status to "completed" (AC #8)
        7. Send Telegram confirmation message (AC #7)
        8. Index sent response to vector DB (AC #9)

        Args:
            update: Telegram Update object with callback_query
            context: Telegram bot context
            email_id: Email ID from callback data "send_response_{email_id}"
            user_id: Database user ID (for GmailClient initialization)

        Raises:
            ValueError: If email not found or missing draft
        """
        query = update.callback_query
        telegram_id = str(query.from_user.id)

        self.logger.info(
            "send_response_callback_received",
            email_id=email_id,
            telegram_id=telegram_id,
            user_id=user_id
        )

        try:
            # Load email and validate draft
            async with self.db_service.async_session() as session:
                email = await session.get(EmailProcessingQueue, email_id)
                if not email:
                    self.logger.error("send_callback_email_not_found", email_id=email_id)
                    await query.answer("❌ Email not found", show_alert=True)
                    return

                # Verify draft_response exists (AC #4 - applies to both original and edited drafts)
                if not email.draft_response or email.draft_response.strip() == "":
                    self.logger.error("send_callback_no_draft", email_id=email_id)
                    await query.answer("❌ No draft available to send", show_alert=True)
                    return

                # Get user for GmailClient
                user = await session.get(User, user_id)
                if not user:
                    self.logger.error("send_callback_user_not_found", user_id=user_id)
                    await query.answer("❌ User not found", show_alert=True)
                    return

                # Answer callback to remove loading state
                await query.answer()

                # Send email via Gmail API (AC #5, #6)
                # GmailClient will use its own DatabaseService instance
                gmail_client = GmailClient(user_id=user.id)

                # Generate reply subject
                reply_subject = email.subject
                if reply_subject and not reply_subject.startswith("Re: "):
                    reply_subject = f"Re: {reply_subject}"

                try:
                    # Send email with threading support (AC #6)
                    # GmailClient.send_email() automatically handles In-Reply-To header via thread_id
                    sent_message_id = await gmail_client.send_email(
                        to=email.sender,
                        subject=reply_subject or "Re: (no subject)",
                        body=email.draft_response,
                        thread_id=email.gmail_thread_id  # AC #6: Proper threading
                    )

                    self.logger.info(
                        "response_sent_via_gmail",
                        email_id=email_id,
                        user_id=user_id,
                        recipient=email.sender,
                        sent_message_id=sent_message_id,
                        gmail_thread_id=email.gmail_thread_id
                    )

                except Exception as gmail_error:
                    self.logger.error(
                        "gmail_send_failed",
                        email_id=email_id,
                        user_id=user_id,
                        error=str(gmail_error),
                        error_type=type(gmail_error).__name__,
                        exc_info=True
                    )
                    await self.telegram_bot.send_message(
                        telegram_id=telegram_id,
                        text=f"❌ Failed to send email: {str(gmail_error)}",
                        user_id=user_id
                    )
                    return

                # Update email status to "completed" (AC #8)
                email.status = "completed"

                # Update WorkflowMapping state
                result = await session.execute(
                    select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
                )
                workflow_mapping = result.scalar_one_or_none()

                if workflow_mapping:
                    workflow_mapping.workflow_state = "sent"

                session.add(email)
                if workflow_mapping:
                    session.add(workflow_mapping)
                await session.commit()

                self.logger.info(
                    "email_status_updated_completed",
                    email_id=email_id,
                    user_id=user_id,
                    status="completed"
                )

                # NOTE: Telegram confirmation will be sent by send_confirmation node
                # This ensures clean UX with only one final summary message
                # (intermediate messages are deleted by send_confirmation)

                # Index sent response to vector DB (AC #9)
                try:
                    indexing_success = await self.index_sent_response(
                        email_id=email_id,
                        session=session
                    )

                    if indexing_success:
                        self.logger.info(
                            "sent_response_indexed",
                            email_id=email_id,
                            user_id=user_id
                        )
                    else:
                        self.logger.warning(
                            "sent_response_indexing_failed",
                            email_id=email_id,
                            user_id=user_id
                        )

                except Exception as indexing_error:
                    # Don't fail send operation if indexing fails
                    self.logger.error(
                        "sent_response_indexing_error",
                        email_id=email_id,
                        user_id=user_id,
                        error=str(indexing_error),
                        error_type=type(indexing_error).__name__,
                        exc_info=True
                    )

        except Exception as e:
            self.logger.error(
                "send_response_callback_failed",
                email_id=email_id,
                telegram_id=telegram_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            await query.answer("❌ Error sending response", show_alert=True)

    async def index_sent_response(
        self,
        email_id: int,
        session
    ) -> bool:
        """Index sent response into vector DB for future RAG context (AC #9).

        Workflow:
        1. Load EmailProcessingQueue record with draft_response
        2. Generate unique document ID for sent response
        3. Generate embedding using EmbeddingService.embed_text()
        4. Store embedding in ChromaDB "email_embeddings" collection
        5. Metadata: sender, subject, date, language, message_id, user_id

        Args:
            email_id: Email ID to index
            session: Active async database session

        Returns:
            bool: True if indexing successful, False otherwise
        """
        try:
            email = await session.get(EmailProcessingQueue, email_id)
            if not email or not email.draft_response:
                self.logger.error(
                    "index_sent_response_no_draft",
                    email_id=email_id
                )
                return False

            # Generate unique document ID for sent response
            sent_message_id = f"sent_{email_id}_{int(datetime.now(UTC).timestamp())}"

            # Generate embedding (AC #9)
            try:
                embedding = self.embedding_service.embed_text(email.draft_response)
            except Exception as embed_error:
                self.logger.error(
                    "embedding_generation_failed",
                    email_id=email_id,
                    error=str(embed_error),
                    exc_info=True
                )
                return False

            # Prepare metadata for vector DB
            reply_subject = email.subject
            if reply_subject and not reply_subject.startswith("Re: "):
                reply_subject = f"Re: {reply_subject}"

            metadata = {
                "message_id": sent_message_id,
                "user_id": email.user_id,
                "thread_id": email.gmail_thread_id,
                "sender": email.sender,  # Original sender (recipient of our response)
                "subject": reply_subject or "Re: (no subject)",
                "date": datetime.now(UTC).isoformat(),
                "language": email.detected_language or "en",
                "tone": email.tone or "professional",
                "is_sent_response": True  # Flag to distinguish from received emails
            }

            # Store in ChromaDB (AC #9)
            try:
                self.vector_db_client.insert_embedding(
                    collection_name="email_embeddings",
                    embedding=embedding,
                    metadata=metadata,
                    id=sent_message_id
                )

                self.logger.info(
                    "sent_response_indexed_to_chromadb",
                    email_id=email_id,
                    user_id=email.user_id,
                    message_id=sent_message_id,
                    embedding_dimension=len(embedding)
                )

                return True

            except Exception as db_error:
                self.logger.error(
                    "vector_db_insert_failed",
                    email_id=email_id,
                    error=str(db_error),
                    exc_info=True
                )
                return False

        except Exception as e:
            self.logger.error(
                "index_sent_response_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return False

    async def handle_reject_response_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        email_id: int,
        user_id: int
    ) -> None:
        """Handle Reject button callback - mark draft as rejected.

        Workflow:
        1. Parse callback_data to extract email_id
        2. Update EmailProcessingQueue.status to "rejected"
        3. Update WorkflowMapping.workflow_state to "rejected"
        4. Send Telegram confirmation message

        Args:
            update: Telegram Update object with callback_query
            context: Telegram bot context
            email_id: Email ID from callback data "reject_response_{email_id}"
            user_id: Database user ID (for logging)
        """
        query = update.callback_query
        telegram_id = str(query.from_user.id)

        self.logger.info(
            "reject_response_callback_received",
            email_id=email_id,
            telegram_id=telegram_id,
            user_id=user_id
        )

        try:
            async with self.db_service.async_session() as session:
                email = await session.get(EmailProcessingQueue, email_id)
                if not email:
                    self.logger.error("reject_callback_email_not_found", email_id=email_id)
                    await query.answer("❌ Email not found", show_alert=True)
                    return

                # Answer callback
                await query.answer()

                # Update status to rejected
                email.status = "rejected"

                # Update WorkflowMapping state
                result = await session.execute(
                    select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
                )
                workflow_mapping = result.scalar_one_or_none()

                if workflow_mapping:
                    workflow_mapping.workflow_state = "rejected"

                session.add(email)
                if workflow_mapping:
                    session.add(workflow_mapping)
                await session.commit()

                self.logger.info(
                    "response_rejected",
                    email_id=email_id,
                    user_id=user_id,
                    status="rejected"
                )

                # Send Telegram confirmation
                confirmation_message = (
                    "❌ *Response draft rejected*\n\n"
                    f"Subject: {email.subject or '(no subject)'}\n\n"
                    "The draft has been discarded."
                )

                await self.telegram_bot.send_message(
                    telegram_id=telegram_id,
                    text=confirmation_message,
                    user_id=user_id
                )

                self.logger.info(
                    "telegram_rejection_confirmation_sent",
                    email_id=email_id,
                    telegram_id=telegram_id
                )

        except Exception as e:
            self.logger.error(
                "reject_response_callback_failed",
                email_id=email_id,
                telegram_id=telegram_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            await query.answer("❌ Error rejecting response", show_alert=True)
