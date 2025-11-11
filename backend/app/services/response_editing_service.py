"""
Response Editing Service

This service handles AI-generated response draft editing workflow in Telegram:
- Edit button callback handling (prompts user for edited text)
- User reply message capture and draft update
- Response draft re-display with updated text

Integrates with:
- TelegramBotClient (Epic 2): Sends messages and handles callbacks
- EmailProcessingQueue (Epic 1-3): Updates draft_response field
- WorkflowMapping (Story 2.6): Tracks workflow state transitions

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.9 (Response Editing and Sending)
"""

import structlog
from typing import Optional
from sqlmodel import Session, select
from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes

from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User
from app.services.database import DatabaseService, database_service
from app.services.telegram_response_draft import TelegramResponseDraftService

logger = structlog.get_logger(__name__)


# User session storage for tracking active edit sessions
# Format: {telegram_id: email_id}
_edit_sessions = {}


class ResponseEditingService:
    """Service for editing AI-generated response drafts via Telegram conversation.

    This service implements the edit workflow (AC #1-3):
    1. User clicks [Edit] button on response draft message
    2. Bot prompts: "Please reply to this message with your edited response:"
    3. User replies with edited text
    4. Bot updates EmailProcessingQueue.draft_response
    5. Bot re-sends draft message with updated text and same buttons
    6. WorkflowMapping.workflow_state updated to "draft_edited"

    Attributes:
        telegram_bot: TelegramBotClient instance for message sending
        db_service: DatabaseService for creating database sessions
        draft_service: TelegramResponseDraftService for re-building draft messages
        logger: Structured logger
    """

    # Message constants
    MAX_EDITED_TEXT_LENGTH = 5000  # Reasonable limit for email response

    def __init__(
        self,
        telegram_bot: TelegramBotClient,
        db_service: DatabaseService = None,
        draft_service: TelegramResponseDraftService = None
    ):
        """Initialize response editing service.

        Args:
            telegram_bot: Initialized TelegramBotClient instance
            db_service: DatabaseService for creating database sessions (defaults to global instance)
            draft_service: TelegramResponseDraftService for re-building draft messages
        """
        self.telegram_bot = telegram_bot
        self.db_service = db_service or database_service
        self.draft_service = draft_service
        self.logger = logger.bind(service="response_editing")

    async def handle_edit_response_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        email_id: int,
        user_id: int
    ) -> None:
        """Handle Edit button callback - prompt user for edited text (AC #1, #2).

        Workflow:
        1. Parse callback_data to extract email_id
        2. Load WorkflowMapping and EmailProcessingQueue records
        3. Send Telegram message: "Please reply to this message with your edited response:"
        4. Store email_id in user session for next message handler
        5. User's next message will be captured by handle_message_reply()

        Args:
            update: Telegram Update object with callback_query
            context: Telegram bot context
            email_id: Email ID from callback data "edit_response_{email_id}"
            user_id: Database user ID (for logging)

        Raises:
            ValueError: If email not found or missing draft
        """
        query = update.callback_query
        telegram_id = str(query.from_user.id)

        self.logger.info(
            "edit_response_callback_received",
            email_id=email_id,
            telegram_id=telegram_id,
            user_id=user_id
        )

        try:
            # Load email and workflow mapping
            async with self.db_service.async_session() as session:
                email = await session.get(EmailProcessingQueue, email_id)
                if not email:
                    self.logger.error("edit_callback_email_not_found", email_id=email_id)
                    await query.answer("❌ Email not found", show_alert=True)
                    return

                if not email.draft_response:
                    self.logger.error("edit_callback_no_draft", email_id=email_id)
                    await query.answer("❌ No draft available to edit", show_alert=True)
                    return

                result = await session.execute(
                    select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
                )
                workflow_mapping = result.scalar_one_or_none()

                if not workflow_mapping:
                    self.logger.error("edit_callback_workflow_not_found", email_id=email_id)
                    await query.answer("❌ Workflow not found", show_alert=True)
                    return

                # Answer callback to remove loading state
                await query.answer()

                # Store email_id in user session for message handler
                _edit_sessions[telegram_id] = email_id

                # Send edit prompt message
                prompt_message = (
                    "✏️ *Edit Response Draft*\n\n"
                    "Please reply to this message with your edited response.\n\n"
                    "📝 Your current draft will be replaced with the new text."
                )

                await self.telegram_bot.send_message(
                    telegram_id=telegram_id,
                    text=prompt_message,
                    user_id=user_id
                )

                self.logger.info(
                    "edit_prompt_sent",
                    email_id=email_id,
                    telegram_id=telegram_id,
                    user_id=user_id
                )

        except Exception as e:
            self.logger.error(
                "edit_response_callback_failed",
                email_id=email_id,
                telegram_id=telegram_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            await query.answer("❌ Error starting edit", show_alert=True)

    async def handle_message_reply(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle user reply message with edited text (AC #2, #3).

        Workflow:
        1. Check if user has active edit session (telegram_id in _edit_sessions)
        2. Validate message text (not empty, length < 5000 chars)
        3. Load EmailProcessingQueue and update draft_response field
        4. Update status to "draft_edited"
        5. Re-send draft message with updated text and same buttons
        6. Clear edit session from user state

        Args:
            update: Telegram Update object with message
            context: Telegram bot context
        """
        telegram_id = str(update.effective_user.id)

        # Check if user has active edit session
        if telegram_id not in _edit_sessions:
            # Not an edit session reply, ignore
            return

        email_id = _edit_sessions[telegram_id]
        edited_text = update.message.text

        self.logger.info(
            "message_reply_received",
            email_id=email_id,
            telegram_id=telegram_id,
            edited_text_length=len(edited_text) if edited_text else 0
        )

        try:
            # Validate edited text
            if not edited_text or edited_text.strip() == "":
                await update.message.reply_text(
                    "❌ Edited text cannot be empty.\n\n"
                    "Please send your edited response."
                )
                return

            if len(edited_text) > self.MAX_EDITED_TEXT_LENGTH:
                await update.message.reply_text(
                    f"❌ Edited text too long ({len(edited_text)} characters).\n\n"
                    f"Maximum length: {self.MAX_EDITED_TEXT_LENGTH} characters."
                )
                return

            # Update draft in database
            async with self.db_service.async_session() as session:
                email = await session.get(EmailProcessingQueue, email_id)
                if not email:
                    self.logger.error("message_reply_email_not_found", email_id=email_id)
                    await update.message.reply_text("❌ Email not found")
                    del _edit_sessions[telegram_id]
                    return

                # Get user for permission check
                user = await session.get(User, email.user_id)
                if not user or user.telegram_id != telegram_id:
                    self.logger.error(
                        "message_reply_unauthorized",
                        email_id=email_id,
                        telegram_id=telegram_id,
                        email_user_id=email.user_id
                    )
                    await update.message.reply_text("❌ Unauthorized")
                    del _edit_sessions[telegram_id]
                    return

                # Update draft_response field (AC #3)
                previous_draft = email.draft_response
                email.draft_response = edited_text
                email.status = "draft_edited"

                # Update WorkflowMapping state
                result = await session.execute(
                    select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
                )
                workflow_mapping = result.scalar_one_or_none()

                if workflow_mapping:
                    workflow_mapping.workflow_state = "draft_edited"

                session.add(email)
                if workflow_mapping:
                    session.add(workflow_mapping)
                await session.commit()

                self.logger.info(
                    "draft_response_updated",
                    email_id=email_id,
                    telegram_id=telegram_id,
                    user_id=email.user_id,
                    previous_draft_length=len(previous_draft) if previous_draft else 0,
                    new_draft_length=len(edited_text)
                )

                # Clear edit session
                del _edit_sessions[telegram_id]

                # Send confirmation
                confirmation_message = (
                    "✅ *Response Updated*\n\n"
                    "Your draft has been updated with the new text.\n\n"
                    "Use the buttons below to send or make further edits."
                )

                await update.message.reply_text(
                    text=confirmation_message,
                    parse_mode="Markdown"
                )

                # Re-send draft message with updated text
                if self.draft_service:
                    try:
                        await self.draft_service.send_response_draft(email_id)
                        self.logger.info(
                            "updated_draft_resent",
                            email_id=email_id,
                            telegram_id=telegram_id
                        )
                    except Exception as resend_error:
                        self.logger.error(
                            "draft_resend_failed",
                            email_id=email_id,
                            error=str(resend_error),
                            exc_info=True
                        )

        except Exception as e:
            self.logger.error(
                "message_reply_failed",
                email_id=email_id,
                telegram_id=telegram_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            await update.message.reply_text("❌ Error updating draft. Please try again.")

            # Clean up session on error
            if telegram_id in _edit_sessions:
                del _edit_sessions[telegram_id]
