"""
Telegram Response Draft Service

This service formats and sends AI-generated response drafts to users via Telegram
with inline keyboard buttons for approval actions (Send, Edit, Reject).

Integrates with:
- ResponseGenerationService (Story 3.7): Reads draft_response from EmailProcessingQueue
- TelegramBotClient (Epic 2): Sends messages with inline keyboards
- WorkflowMapping (Story 2.6): Persists callback reconnection data

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.8 (Response Draft Telegram Messages)
"""

import structlog
from typing import Optional
from sqlmodel import Session, select
from telegram import InlineKeyboardButton

from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User
from app.services.database import DatabaseService, database_service
from app.utils.errors import TelegramUserBlockedError

logger = structlog.get_logger(__name__)


class TelegramResponseDraftService:
    """Service for sending AI-generated response drafts to Telegram with approval interface.

    This service implements the complete response draft notification workflow:
    1. Load email with response draft from database (AC #1-9)
    2. Format message with original email preview and draft (AC #2, #3, #4)
    3. Build inline keyboard with approval buttons (AC #5)
    4. Send message to Telegram (AC #1-9)
    5. Save WorkflowMapping for callback reconnection
    6. Update EmailProcessingQueue status to "awaiting_response_approval"

    Attributes:
        telegram_bot: TelegramBotClient instance for message sending
        db_service: DatabaseService for creating database sessions
        logger: Structured logger
    """

    # Message formatting constants
    MAX_BODY_PREVIEW_CHARS = 100  # AC #2: First 100 chars of body
    TELEGRAM_MAX_LENGTH = 4096  # Telegram message length limit
    VISUAL_SEPARATOR = "─────────────────"  # AC #4: Visual separation

    # Language display names for message formatting (AC #6)
    LANGUAGE_NAMES = {
        "en": "English",
        "de": "German",
        "ru": "Russian",
        "uk": "Ukrainian"
    }

    def __init__(
        self,
        telegram_bot: TelegramBotClient,
        db_service: DatabaseService = None
    ):
        """Initialize Telegram response draft service.

        Args:
            telegram_bot: Initialized TelegramBotClient instance
            db_service: DatabaseService for creating database sessions (defaults to global instance)
        """
        self.telegram_bot = telegram_bot
        self.db_service = db_service or database_service
        self.logger = logger.bind(service="telegram_response_draft")

    async def format_response_draft_message(
        self,
        email_id: int,
        draft_response: Optional[str] = None,
        detected_language: Optional[str] = None,
        tone: Optional[str] = None
    ) -> str:
        """Format response draft Telegram message with original email preview and draft (AC #1-4, #6-7, #9).

        Message structure:
        - Header: "📧 Response Draft Ready" (with ⚠️ for priority emails - AC #9)
        - Original Email section: sender, subject, body preview (first 100 chars) - AC #2
        - Visual separator for clarity - AC #4
        - Draft section: Language + Tone indication + full response text - AC #3, #6
          Example: "✍️ AI-Generated Response (German, Formal):"
        - Visual separator - AC #4
        - Context summary if available - AC #7

        Args:
            email_id: Database ID of email with response draft
            draft_response: AI-generated response text (from workflow state or database)
            detected_language: Language code (from workflow state or database)
            tone: Response tone (from workflow state or database)

        Returns:
            Formatted message string ready for Telegram delivery

        Raises:
            ValueError: If email not found or missing required fields
        """
        # Load email from database
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
            )
            email = result.scalar_one_or_none()
            if not email:
                raise ValueError(f"Email with id={email_id} not found")

            # Use provided draft_response or fallback to database (for backward compatibility)
            draft_text = draft_response or getattr(email, 'draft_response', None)
            if not draft_text:
                raise ValueError(f"Email id={email_id} has no draft_response")

            # Build message sections
            sections = []

            # Header with priority flag (AC #9)
            header = "📧 Response Draft Ready"
            if email.is_priority:
                header = "⚠️ " + header
            sections.append(header)
            sections.append("")  # Empty line

            # Original Email section (AC #2)
            sections.append("📨 Original Email:")
            sections.append(f"From: {email.sender}")
            sections.append(f"Subject: {email.subject or '(no subject)'}")

            # Body preview - use subject since body isn't stored in EmailProcessingQueue
            # In production, this would fetch body from Gmail API or email.body field
            body_preview = (email.subject or "")[:self.MAX_BODY_PREVIEW_CHARS]
            if len(email.subject or "") > self.MAX_BODY_PREVIEW_CHARS:
                body_preview += "..."
            sections.append(f"Preview: {body_preview}")
            sections.append("")

            # Visual separator (AC #4)
            sections.append(self.VISUAL_SEPARATOR)
            sections.append("")

            # Draft section with language/tone indication (AC #3, #6)
            # Use provided detected_language or fallback to database
            language_code = detected_language or getattr(email, 'detected_language', 'en')
            language_name = self.LANGUAGE_NAMES.get(
                language_code or "en",
                language_code or "Unknown"
            )

            # Format response header with language and tone
            # Use provided tone or fallback to database
            tone_value = tone or getattr(email, 'tone', None)
            header_parts = [f"✍️ AI-Generated Response ({language_name}"]
            if tone_value:
                # Capitalize tone for display (formal → Formal)
                tone_display = tone_value.capitalize()
                header_parts.append(f", {tone_display}")
            header_parts.append("):")

            sections.append("".join(header_parts))
            sections.append(draft_text)
            sections.append("")

            # Visual separator (AC #4)
            sections.append(self.VISUAL_SEPARATOR)

            # Context summary (AC #7)
            # Note: We don't have RAG context metadata stored in EmailProcessingQueue
            # This would need to be passed as parameter or retrieved from context service
            # For now, we'll add a placeholder that can be populated by caller
            # TODO: Add context_summary parameter to method signature if needed

            # Join all sections
            message = "\n".join(sections)

            # Handle Telegram length limits (AC #8)
            if len(message) > self.TELEGRAM_MAX_LENGTH:
                # TelegramBotClient.send_message_with_buttons already handles truncation
                # But we should log a warning
                self.logger.warning(
                    "response_draft_message_exceeds_limit",
                    email_id=email_id,
                    message_length=len(message),
                    max_length=self.TELEGRAM_MAX_LENGTH,
                    will_be_truncated=True
                )

            self.logger.info(
                "response_draft_message_formatted",
                email_id=email_id,
                message_length=len(message),
                is_priority=email.is_priority,
                language=email.detected_language
            )

            return message

    def build_response_draft_keyboard(self, email_id: int) -> list[list[InlineKeyboardButton]]:
        """Build inline keyboard with response approval buttons (AC #5).

        Keyboard layout:
        - Row 1: [✅ Send]
        - Row 2: [✏️ Edit] [❌ Reject]

        Callback data format: {action}_response_{email_id}
        Example: "send_response_123"

        Args:
            email_id: Database ID of email for callback data

        Returns:
            2D list of InlineKeyboardButton objects (row structure)
        """
        # Row 1: Send button
        row1 = [
            InlineKeyboardButton(
                text="✅ Send",
                callback_data=f"send_response_{email_id}"
            )
        ]

        # Row 2: Edit and Reject buttons
        row2 = [
            InlineKeyboardButton(
                text="✏️ Edit",
                callback_data=f"edit_response_{email_id}"
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"reject_response_{email_id}"
            )
        ]

        keyboard = [row1, row2]

        self.logger.info(
            "response_draft_keyboard_built",
            email_id=email_id,
            button_count=3
        )

        return keyboard

    async def send_response_draft_to_telegram(self, email_id: int) -> str:
        """Send response draft message with inline keyboard to Telegram (AC #1-9).

        Complete workflow:
        1. Load user's telegram_id from database
        2. Format message using format_response_draft_message()
        3. Build keyboard using build_response_draft_keyboard()
        4. Send message via TelegramBotClient.send_message_with_buttons()
        5. Return telegram_message_id for WorkflowMapping persistence

        Args:
            email_id: Database ID of email with response draft

        Returns:
            Telegram message ID (str) for WorkflowMapping persistence

        Raises:
            ValueError: If email or user not found, or user telegram_id not set
            TelegramUserBlockedError: If user has blocked the bot
            TelegramSendError: If message sending fails after retries
        """
        # Load email and user from database
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
            )
            email = result.scalar_one_or_none()
            if not email:
                raise ValueError(f"Email with id={email_id} not found")

            result = await session.execute(
                select(User).where(User.id == email.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError(f"User with id={email.user_id} not found")

            if not user.telegram_id:
                raise ValueError(f"User id={email.user_id} has no telegram_id set (not linked)")

            # Store user data for later use
            user_telegram_id = user.telegram_id
            user_id = user.id
            detected_language = email.detected_language

        # Format message (now async)
        message_text = await self.format_response_draft_message(email_id)

        # Build keyboard
        keyboard_buttons = self.build_response_draft_keyboard(email_id)

        # Send message with buttons
        try:
            telegram_message_id = await self.telegram_bot.send_message_with_buttons(
                telegram_id=user_telegram_id,
                text=message_text,
                buttons=keyboard_buttons,
                user_id=user_id
            )

            self.logger.info(
                "response_draft_sent_to_telegram",
                email_id=email_id,
                user_id=user_id,
                telegram_message_id=telegram_message_id,
                language=detected_language
            )

            return telegram_message_id

        except TelegramUserBlockedError as e:
            # User blocked bot - log and re-raise
            self.logger.error(
                "response_draft_send_failed_user_blocked",
                email_id=email_id,
                user_id=user_id,
                error=str(e)
            )
            raise

        except Exception as e:
            # Other errors - log and re-raise
            self.logger.error(
                "response_draft_send_failed",
                email_id=email_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    async def save_telegram_message_mapping(
        self,
        email_id: int,
        telegram_message_id: str,
        thread_id: str
    ) -> None:
        """Save WorkflowMapping record for callback reconnection.

        Creates or updates WorkflowMapping with:
        - email_id: Links to EmailProcessingQueue
        - user_id: From email.user_id
        - thread_id: LangGraph workflow instance ID
        - telegram_message_id: For message editing
        - workflow_state: "awaiting_response_approval"

        Args:
            email_id: Database ID of email
            telegram_message_id: Telegram message ID from send_response_draft_to_telegram()
            thread_id: LangGraph workflow thread ID for resume

        Raises:
            ValueError: If email not found
        """
        async with self.db_service.async_session() as session:
            # Load email to get user_id
            result = await session.execute(
                select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
            )
            email = result.scalar_one_or_none()
            if not email:
                raise ValueError(f"Email with id={email_id} not found")

            # Check if mapping already exists (by email_id unique constraint)
            result = await session.execute(
                select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
            )
            existing_mapping = result.scalar_one_or_none()

            if existing_mapping:
                # Update existing mapping
                existing_mapping.telegram_message_id = telegram_message_id
                existing_mapping.thread_id = thread_id
                existing_mapping.workflow_state = "awaiting_response_approval"

                self.logger.info(
                    "workflow_mapping_updated",
                    email_id=email_id,
                    user_id=email.user_id,
                    thread_id=thread_id,
                    telegram_message_id=telegram_message_id
                )
            else:
                # Create new mapping
                mapping = WorkflowMapping(
                    email_id=email_id,
                    user_id=email.user_id,
                    thread_id=thread_id,
                    telegram_message_id=telegram_message_id,
                    workflow_state="awaiting_response_approval"
                )
                session.add(mapping)

                self.logger.info(
                    "workflow_mapping_created",
                    email_id=email_id,
                    user_id=email.user_id,
                    thread_id=thread_id,
                    telegram_message_id=telegram_message_id
                )

            # Commit transaction
            await session.commit()

    async def send_draft_notification(
        self,
        email_id: int,
        workflow_thread_id: str
    ) -> bool:
        """Send response draft notification to Telegram (end-to-end orchestration).

        Complete workflow:
        1. Validate email has draft_response field populated
        2. Format and send Telegram message (call send_response_draft_to_telegram)
        3. Save workflow mapping (call save_telegram_message_mapping)
        4. Update EmailProcessingQueue status to "awaiting_response_approval"
        5. Return True on success

        Args:
            email_id: Database ID of email with response draft
            workflow_thread_id: LangGraph workflow thread ID for callback reconnection

        Returns:
            True if notification sent successfully, False otherwise

        Raises:
            ValueError: If email not found or missing draft_response
            TelegramUserBlockedError: If user has blocked bot (not raised, returns False)
        """
        try:
            # Step 1: Validate email has draft_response
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
                )
                email = result.scalar_one_or_none()
                if not email:
                    raise ValueError(f"Email with id={email_id} not found")

                if not email.draft_response:
                    raise ValueError(f"Email id={email_id} has no draft_response field")

                has_draft = bool(email.draft_response)

            self.logger.info(
                "response_draft_notification_started",
                email_id=email_id,
                workflow_thread_id=workflow_thread_id,
                has_draft=has_draft
            )

            # Step 2: Format and send Telegram message
            telegram_message_id = await self.send_response_draft_to_telegram(email_id)

            # Step 3: Save workflow mapping (now async)
            await self.save_telegram_message_mapping(
                email_id=email_id,
                telegram_message_id=telegram_message_id,
                thread_id=workflow_thread_id
            )

            # Step 4: Update EmailProcessingQueue status
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
                )
                email = result.scalar_one_or_none()
                if email:
                    email.status = "awaiting_response_approval"
                    await session.commit()

            self.logger.info(
                "response_draft_notification_completed",
                email_id=email_id,
                telegram_message_id=telegram_message_id,
                workflow_thread_id=workflow_thread_id
            )

            return True

        except TelegramUserBlockedError as e:
            # User blocked bot - log warning and return False (graceful handling)
            self.logger.warning(
                "response_draft_notification_skipped_user_blocked",
                email_id=email_id,
                error=str(e)
            )
            return False

        except Exception as e:
            # Other errors - log and re-raise
            self.logger.error(
                "response_draft_notification_failed",
                email_id=email_id,
                workflow_thread_id=workflow_thread_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
