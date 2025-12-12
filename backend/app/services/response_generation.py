"""
AI Response Generation Service

This service orchestrates the complete email response generation workflow by integrating:
- Context Retrieval (Story 3.4): Smart Hybrid RAG for conversation context
- Language Detection (Story 3.5): Detect email language (ru/uk/en/de)
- Tone Detection (Story 3.6): Determine response tone (formal/professional/casual)
- Prompt Engineering (Story 3.6): Format prompts with RAG context
- Gemini LLM (Story 2.1): Generate response text

The service follows the Epic 3 architecture pattern with dependency injection for testability.

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.7 (AI Response Generation Service)
"""

import re
import structlog
from typing import Optional, Tuple
from datetime import datetime
from sqlmodel import Session, select

from app.services.database import database_service
from app.core.groq_client import GroqLLMClient as LLMClient
from app.models.email import EmailProcessingQueue
from app.models.context_models import RAGContext
from app.services.context_retrieval import ContextRetrievalService
from app.services.language_detection import LanguageDetectionService
from app.services.tone_detection import ToneDetectionService
from app.prompts.response_generation import format_response_prompt


logger = structlog.get_logger(__name__)


class ResponseGenerationService:
    """Service for generating contextually appropriate email response drafts using RAG.

    This service implements the complete response generation workflow:
    1. Response need classification (AC #2)
    2. RAG context retrieval (AC #3)
    3. Language detection (AC #4)
    4. Tone detection (AC #5)
    5. Prompt formatting (AC #6)
    6. LLM response generation (AC #7)
    7. Response quality validation (AC #9)
    8. Database persistence (AC #8, #10)

    Attributes:
        user_id: Database ID of user
        context_service: ContextRetrievalService for RAG context
        language_service: LanguageDetectionService for language detection
        tone_service: ToneDetectionService for tone detection
        llm_client: LLMClient for Gemini API calls
        db_service: DatabaseService for database operations
        logger: Structured logger
    """

    # Response classification patterns
    NO_REPLY_PATTERNS = [
        r"no-?reply",
        r"noreply",
        r"do-?not-?reply",
        r"newsletter",
        r"notifications?",
        r"automated?",
        r"mailer-daemon"
    ]

    # Question indicators in 4 languages (AC #2)
    QUESTION_INDICATORS = {
        "en": ["?", "what", "when", "where", "who", "why", "how", "can you", "could you", "would you"],
        "de": ["?", "was", "wann", "wo", "wer", "warum", "wie", "können sie", "könnten sie", "würden sie"],
        "ru": ["?", "что", "когда", "где", "кто", "почему", "как", "можете ли", "не могли бы"],
        "uk": ["?", "що", "коли", "де", "хто", "чому", "як", "чи можете", "чи не могли б"]
    }

    # Response quality validation thresholds (AC #9)
    MIN_RESPONSE_LENGTH = 50  # Minimum characters
    MAX_RESPONSE_LENGTH = 2000  # Maximum characters
    MIN_VALID_LENGTH = 20  # Absolute minimum (not empty check)

    # Performance target (NFR001)
    TARGET_GENERATION_TIME = 8.0  # ~8 seconds total

    def __init__(
        self,
        user_id: int,
        context_service: Optional[ContextRetrievalService] = None,
        language_service: Optional[LanguageDetectionService] = None,
        tone_service: Optional[ToneDetectionService] = None,
        llm_client: Optional[LLMClient] = None,
        db_service = None,
    ):
        """Initialize response generation service for specific user.

        Args:
            user_id: Database ID of user
            context_service: Optional ContextRetrievalService for dependency injection (testing)
            language_service: Optional LanguageDetectionService for dependency injection (testing)
            tone_service: Optional ToneDetectionService for dependency injection (testing)
            llm_client: Optional LLMClient for dependency injection (testing)
            db_service: Optional DatabaseService for dependency injection (testing)

        Example:
            # Production usage
            service = ResponseGenerationService(user_id=123)

            # Test usage with mocks
            service = ResponseGenerationService(
                user_id=123,
                context_service=mock_context,
                language_service=mock_language,
                tone_service=mock_tone,
                llm_client=mock_llm
            )
        """
        self.user_id = user_id
        self.db_service = db_service or database_service

        # Initialize services with dependency injection pattern
        self.context_service = context_service or ContextRetrievalService(user_id=user_id)
        self.language_service = language_service or LanguageDetectionService()
        self.tone_service = tone_service or ToneDetectionService()
        self.llm_client = llm_client or LLMClient()

        self.logger = logger.bind(
            service="response_generation",
            user_id=user_id
        )

        self.logger.info(
            "response_generation_service_initialized",
            target_generation_time=self.TARGET_GENERATION_TIME
        )

    async def should_generate_response(self, email: EmailProcessingQueue, db_session=None) -> bool:
        """[DEPRECATED] Determine if email requires a response draft (AC #2).

        **DEPRECATION NOTICE:**
        This rule-based classification method has been replaced by unified LLM classification
        in EmailClassificationService. The LLM now determines needs_response using AI analysis
        with RAG context, providing more accurate classification than these hard-coded rules.

        **New approach (unified LLM call):**
        - EmailClassificationService.classify_email() returns ClassificationResponse
        - ClassificationResponse includes: suggested_folder, needs_response, response_draft
        - Single LLM call instead of 2-3 separate calls (quota optimization)
        - Uses RAG context (thread history + semantic search) for better accuracy

        **Do not use this method in new code.** It remains only for backwards compatibility
        with existing tests. Workflow nodes now use ClassificationResponse.needs_response.

        Old classification logic:
        - Return False if sender is no-reply/automated/newsletter
        - Return True if email contains question indicators
        - Return True if email is part of active conversation (>2 in thread)
        - Return False for likely automated messages
        - Default: True (generate response for unclear cases) ← Too aggressive, caused false positives

        Args:
            email: Email object to classify
            db_session: Optional AsyncSession for database queries (required for thread count check)

        Returns:
            True if response should be generated, False to skip

        Example:
            >>> service = ResponseGenerationService(user_id=1)
            >>> needs_response = await service.should_generate_response(email, db_session)
            >>> print(needs_response)  # True or False
        """
        sender_lower = email.sender.lower()

        # Check for no-reply/automated senders (AC #2)
        for pattern in self.NO_REPLY_PATTERNS:
            if re.search(pattern, sender_lower, re.IGNORECASE):
                self.logger.info(
                    "response_classification_no_reply",
                    email_id=email.id,
                    sender=email.sender[:50],  # Privacy: truncate
                    reason="automated_sender"
                )
                return False

        # Check email subject for question indicators in all languages (AC #2)
        # Note: EmailProcessingQueue doesn't store body, so we use subject for classification
        email_text_lower = (email.subject or "").lower()

        for lang_indicators in self.QUESTION_INDICATORS.values():
            for indicator in lang_indicators:
                if indicator.lower() in email_text_lower:
                    self.logger.info(
                        "response_classification_question_detected",
                        email_id=email.id,
                        indicator=indicator,
                        reason="contains_question"
                    )
                    return True

        # Check if part of active conversation (>2 emails in thread)
        # This would require querying thread length - for now, check if thread_id exists
        if email.gmail_thread_id and db_session:
            # Count emails in same thread using provided async session
            thread_result = await db_session.execute(
                select(EmailProcessingQueue)
                .where(EmailProcessingQueue.gmail_thread_id == email.gmail_thread_id)
                .where(EmailProcessingQueue.user_id == self.user_id)
            )
            thread_count = thread_result.scalars().all()

            if len(thread_count) > 2:
                self.logger.info(
                    "response_classification_active_thread",
                    email_id=email.id,
                    thread_length=len(thread_count),
                    reason="ongoing_conversation"
                )
                return True

        # Default: generate response for unclear cases (AC #2)
        # Better to offer a response than miss an important email
        self.logger.info(
            "response_classification_default_generate",
            email_id=email.id,
            reason="unclear_default_to_generate"
        )
        return True

    async def generate_response(self, email_id: int) -> Optional[str]:
        """Generate AI response draft for email using RAG context (AC #1, #3-#7).

        Complete workflow:
        1. Load email from database
        2. Check if response needed (call should_generate_response)
        3. Retrieve RAG context (call ContextRetrievalService.retrieve_context)
        4. Detect language (call LanguageDetectionService.detect)
        5. Detect tone (call ToneDetectionService.detect_tone)
        6. Format prompt (call format_response_prompt)
        7. Generate response (call LLMClient.send_prompt)

        Args:
            email_id: Database ID of email to generate response for

        Returns:
            Generated response draft string, or None if no response needed

        Raises:
            ValueError: If email not found
            Exception: If any service call fails

        Example:
            >>> service = ResponseGenerationService(user_id=1)
            >>> response = await service.generate_response(email_id=42)
            >>> print(response)  # "Dear Sir/Madam, Thank you for..."
        """
        start_time = datetime.now()

        # Load email from database
        async with self.db_service.async_session() as session:
            result = await session.execute(
                select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
            )
            email = result.scalar_one_or_none()
            if not email:
                raise ValueError(f"Email with id={email_id} not found")

            # Check if response needed (AC #2)
            if not await self.should_generate_response(email, db_session=session):
                self.logger.info(
                    "response_generation_skipped",
                    email_id=email_id,
                    reason="no_response_needed"
                )
                return None

            self.logger.info(
                "response_generation_started",
                email_id=email_id,
                sender=email.sender[:50]  # Privacy: truncate
            )

            try:
                # Step 1: Retrieve RAG context (AC #3)
                rag_context: RAGContext = await self.context_service.retrieve_context(email_id)
                self.logger.info(
                    "response_generation_context_retrieved",
                    email_id=email_id,
                    thread_length=len(rag_context["thread_history"]),
                    semantic_count=len(rag_context["semantic_results"]),
                    total_tokens=rag_context["metadata"].get("total_tokens_used", 0)
                )

                # Step 2: Detect language (AC #4)
                # Note: EmailProcessingQueue doesn't store body, use subject for detection
                # In production, body would be fetched from Gmail API here
                email_text = email.subject or ''
                language_code, confidence = self.language_service.detect(email_text)
                self.logger.info(
                    "response_generation_language_detected",
                    email_id=email_id,
                    language=language_code,
                    confidence=confidence
                )

                # Step 3: Detect tone (AC #5)
                # Get thread history emails for tone detection
                thread_history_emails = []
                if rag_context["thread_history"]:
                    # Convert EmailMessage TypedDict to EmailProcessingQueue for tone detection
                    # For now, we'll pass the current email and let tone service handle it
                    pass

                tone = self.tone_service.detect_tone(email, thread_history=None)
                self.logger.info(
                    "response_generation_tone_detected",
                    email_id=email_id,
                    tone=tone
                )

                # Step 4: Format prompt (AC #6)
                formatted_prompt = format_response_prompt(
                    email=email,
                    rag_context=rag_context,
                    language=language_code,
                    tone=tone
                )
                prompt_length = len(formatted_prompt)
                self.logger.info(
                    "response_generation_prompt_formatted",
                    email_id=email_id,
                    prompt_length=prompt_length,
                    language=language_code,
                    tone=tone
                )

                # Step 5: Generate response with Gemini (AC #7)
                response_draft = self.llm_client.send_prompt(
                    prompt=formatted_prompt,
                    response_format="text",
                    operation="response_generation"
                )

                # Save detected language and tone to email record (AC #8)
                email.detected_language = language_code
                email.tone = tone
                session.add(email)
                await session.commit()
                await session.refresh(email)

                generation_time = (datetime.now() - start_time).total_seconds()
                self.logger.info(
                    "response_generation_completed",
                    email_id=email_id,
                    response_length=len(response_draft),
                    generation_time=generation_time,
                    target_time=self.TARGET_GENERATION_TIME,
                    language=language_code,
                    tone=tone
                )

                return response_draft

            except Exception as e:
                self.logger.error(
                    "response_generation_failed",
                    email_id=email_id,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise

    def validate_response(self, response_draft: str, expected_language: str) -> bool:
        """Validate response quality before presenting to user (AC #9).

        Validation checks:
        1. Not empty (minimum 20 characters)
        2. Appropriate length (50-2000 characters)
        3. Correct language (matches expected)
        4. Basic structure (contains greeting and closing indicators)

        Args:
            response_draft: Generated response text to validate
            expected_language: Expected language code (de, en, ru, uk)

        Returns:
            True if valid, False otherwise

        Example:
            >>> service = ResponseGenerationService(user_id=1)
            >>> is_valid = service.validate_response(response_draft, "de")
            >>> print(is_valid)  # True or False
        """
        # Check 1: Not empty (minimum 20 characters)
        if not response_draft or len(response_draft) < self.MIN_VALID_LENGTH:
            self.logger.warning(
                "response_validation_failed",
                reason="too_short",
                length=len(response_draft) if response_draft else 0,
                min_length=self.MIN_VALID_LENGTH
            )
            return False

        # Check 2: Appropriate length (50-2000 characters)
        if len(response_draft) < self.MIN_RESPONSE_LENGTH:
            self.logger.warning(
                "response_validation_failed",
                reason="below_min_length",
                length=len(response_draft),
                min_length=self.MIN_RESPONSE_LENGTH
            )
            return False

        if len(response_draft) > self.MAX_RESPONSE_LENGTH:
            self.logger.warning(
                "response_validation_failed",
                reason="above_max_length",
                length=len(response_draft),
                max_length=self.MAX_RESPONSE_LENGTH
            )
            return False

        # Check 3: Correct language (AC #9)
        try:
            detected_lang, confidence = self.language_service.detect(response_draft)
            if detected_lang != expected_language:
                self.logger.warning(
                    "response_validation_failed",
                    reason="language_mismatch",
                    expected=expected_language,
                    detected=detected_lang,
                    confidence=confidence
                )
                return False
        except Exception as e:
            self.logger.warning(
                "response_validation_language_check_failed",
                error=str(e),
                proceeding_anyway=True
            )
            # Don't fail validation if language detection fails

        # Check 4: Basic structure check (greeting and closing)
        # Common greeting patterns in 4 languages
        greeting_patterns = [
            r"dear\s+",  # English
            r"sehr geehrte",  # German formal
            r"liebe",  # German casual
            r"уважаем",  # Russian formal
            r"доброго дня",  # Ukrainian
            r"здравствуй",  # Russian casual
        ]

        closing_patterns = [
            r"sincerely",
            r"best regards",
            r"с уважением",
            r"з повагою",
            r"mit freundlichen grüßen",
            r"viele grüße",
        ]

        has_greeting = any(re.search(pattern, response_draft.lower()) for pattern in greeting_patterns)
        has_closing = any(re.search(pattern, response_draft.lower()) for pattern in closing_patterns)

        if not (has_greeting or has_closing):
            self.logger.warning(
                "response_validation_structure_warning",
                reason="missing_greeting_or_closing",
                has_greeting=has_greeting,
                has_closing=has_closing,
                proceeding_anyway=True
            )
            # This is a warning, not a hard failure
            # Some valid responses might not match our patterns

        self.logger.info(
            "response_validation_passed",
            length=len(response_draft),
            language=expected_language,
            has_greeting=has_greeting,
            has_closing=has_closing
        )

        return True

    def save_response_draft(
        self,
        email_id: int,
        response_draft: str,
        language: str,
        tone: str
    ) -> None:
        """Save generated response draft to database (AC #8, #10).

        Updates EmailProcessingQueue record with:
        - draft_response: Generated response text
        - detected_language: Language code
        - tone: Detected tone (formal/professional/casual)
        - status: "awaiting_approval"
        - classification: "needs_response"
        - updated_at: NOW()

        Args:
            email_id: Database ID of email
            response_draft: Generated response text
            language: Detected language code
            tone: Detected tone

        Raises:
            ValueError: If email not found

        Example:
            >>> service = ResponseGenerationService(user_id=1)
            >>> service.save_response_draft(42, "Dear...", "de", "formal")
        """
        with Session(self.db_service.engine) as session:
            email = session.get(EmailProcessingQueue, email_id)
            if not email:
                raise ValueError(f"Email with id={email_id} not found")

            # Update fields (AC #8, #10)
            email.draft_response = response_draft
            email.detected_language = language
            email.tone = tone  # Story 3.6: Save detected tone (formal/professional/casual)
            email.status = "awaiting_approval"  # AC #10
            email.classification = "needs_response"  # AC #10 (differentiates from sort_only)
            email.updated_at = datetime.now()

            session.add(email)
            session.commit()

            self.logger.info(
                "response_draft_saved",
                email_id=email_id,
                response_length=len(response_draft),
                language=language,
                tone=tone,
                status=email.status,
                classification=email.classification
            )

    async def process_email_for_response(self, email_id: int) -> bool:
        """End-to-end orchestration: generate, validate, and save response (AC #1-#10).

        Complete workflow:
        1. Load email from database
        2. Check if response needed (should_generate_response)
        3. Generate response (generate_response)
        4. Validate response quality (validate_response)
        5. Save to database (save_response_draft)

        Args:
            email_id: Database ID of email to process

        Returns:
            True if response generated successfully, False if no response needed

        Raises:
            ValueError: If email not found
            Exception: If generation or validation fails

        Example:
            >>> service = ResponseGenerationService(user_id=1)
            >>> success = await service.process_email_for_response(email_id=42)
            >>> print(success)  # True or False
        """
        start_time = datetime.now()

        self.logger.info(
            "process_email_for_response_started",
            email_id=email_id
        )

        try:
            # Step 1: Generate response (includes classification check)
            response_draft = await self.generate_response(email_id)

            # Step 2: Check if response was generated
            if response_draft is None:
                # No response needed (newsletter, no-reply, etc.)
                self.logger.info(
                    "process_email_for_response_skipped",
                    email_id=email_id,
                    reason="no_response_needed"
                )
                return False

            # Step 3: Detect language for validation
            with Session(self.db_service.engine) as session:
                email = session.get(EmailProcessingQueue, email_id)
                if not email:
                    raise ValueError(f"Email with id={email_id} not found")

                # Note: EmailProcessingQueue doesn't store body, use subject for detection
                email_text = email.subject or ''
                language_code, _ = self.language_service.detect(email_text)
                tone = self.tone_service.detect_tone(email, thread_history=None)

            # Step 4: Validate response quality
            is_valid = self.validate_response(response_draft, language_code)

            if not is_valid:
                error_msg = "Response validation failed: quality check did not pass"
                self.logger.error(
                    "process_email_for_response_validation_failed",
                    email_id=email_id,
                    response_length=len(response_draft)
                )
                raise ValueError(error_msg)

            # Step 5: Save to database
            self.save_response_draft(email_id, response_draft, language_code, tone)

            total_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                "process_email_for_response_completed",
                email_id=email_id,
                total_time=total_time,
                target_time=self.TARGET_GENERATION_TIME
            )

            return True

        except Exception as e:
            self.logger.error(
                "process_email_for_response_failed",
                email_id=email_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
