"""Email classification service using Gemini LLM.

This service analyzes email content and classifies it into user-defined folder categories
using AI-powered classification with Gemini 2.5 Flash. It integrates with Gmail API for
email retrieval and uses prompt engineering from Story 2.2.

Usage:
    service = EmailClassificationService(db_session, gmail_client, llm_client)
    result = await service.classify_email(email_id=123, user_id=456)
    # Returns: ClassificationResponse(suggested_folder="Work", reasoning="...", ...)
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, List
from pydantic import ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.gmail_client import GmailClient
from app.core.groq_client import GroqLLMClient as LLMClient
from app.models.classification_response import ClassificationResponse
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.models.context_models import RAGContext, EmailMessage
from app.prompts.classification_prompt import build_classification_prompt
from app.services.context_retrieval import ContextRetrievalService
from app.utils.errors import (
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GmailAPIError,
)


logger = structlog.get_logger(__name__)


def _format_rag_context(rag_context: RAGContext) -> str:
    """Format RAGContext into human-readable string for LLM prompt.

    Converts the structured RAGContext with thread_history, sender_history, and semantic_results
    into a formatted text block that provides conversation context to the LLM.

    Args:
        rag_context: RAGContext dict with thread_history, sender_history, semantic_results, metadata

    Returns:
        Formatted string with thread history, sender history, and semantic results, or empty string if no context

    Example:
        >>> rag_context = {
        ...     "thread_history": [{"sender": "tax@example.com", "subject": "Tax documents", ...}],
        ...     "sender_history": [{"sender": "tax@example.com", "subject": "Previous tax email", ...}],
        ...     "semantic_results": [],
        ...     "metadata": {"thread_length": 1, "sender_history_count": 5, "semantic_count": 0, ...}
        ... }
        >>> formatted = _format_rag_context(rag_context)
        >>> print(formatted)
        **Thread History (1 emails in conversation):**
        ...
        **Full Conversation with Sender (Last 90 Days - 5 emails):**
        ...
    """
    if not rag_context:
        return ""

    thread_history = rag_context.get("thread_history", [])
    sender_history = rag_context.get("sender_history", [])
    semantic_results = rag_context.get("semantic_results", [])
    metadata = rag_context.get("metadata", {})

    # If no context available, return empty string
    if not thread_history and not sender_history and not semantic_results:
        return "No related emails found."

    formatted_parts = []

    # Format thread history
    if thread_history:
        thread_length = metadata.get("thread_length", len(thread_history))
        formatted_parts.append(f"**Thread History ({thread_length} emails in conversation):**\n")
        formatted_parts.append("(Same thread as current email)\n")

        for i, email in enumerate(thread_history, 1):
            # Show more context for better AI understanding (500 chars instead of 200)
            body_preview = email['body'][:500] if len(email['body']) > 500 else email['body']
            formatted_parts.append(
                f"{i}. From: {email['sender']}\n"
                f"   Subject: {email['subject']}\n"
                f"   Date: {email['date']}\n"
                f"   Body: {body_preview}{'...' if len(email['body']) > 500 else ''}\n"
            )

    # Format sender conversation history (NEW - Critical for cross-thread context!)
    if sender_history:
        sender_history_count = metadata.get("sender_history_count", len(sender_history))
        formatted_parts.append(f"\n**Full Conversation with Sender (Last 90 Days - {sender_history_count} emails):**\n")
        formatted_parts.append("(COMPLETE chronological history sorted OLDEST → NEWEST by Date)\n")
        formatted_parts.append("(⚠️ CRITICAL: Analyze dates to understand timeline of discussion evolution)\n")
        formatted_parts.append("(Use this historical context to see what plans were made, what was agreed upon, and how the conversation developed over time)\n")

        for i, email in enumerate(sender_history, 1):
            # Show MORE context for sender history (700 chars) as this is critical for understanding
            # conversations that span multiple threads (e.g., "Re: Праздники" referencing "Праздники 2025")
            body_preview = email['body'][:700] if len(email['body']) > 700 else email['body']

            formatted_parts.append(
                f"{i}. From: {email['sender']}\n"
                f"   Subject: {email['subject']}\n"
                f"   Date: {email['date']}\n"
                f"   Body: {body_preview}{'...' if len(email['body']) > 700 else ''}\n"
            )

    # Format semantic results
    if semantic_results:
        semantic_count = metadata.get("semantic_count", len(semantic_results))
        formatted_parts.append(f"\n**Related Emails (top {semantic_count} similar):**\n")
        formatted_parts.append("(From DIFFERENT threads with same sender - may contain relevant context)\n")

        for i, email in enumerate(semantic_results, 1):
            # Show more context for cross-thread understanding (500 chars instead of 200)
            # This is crucial for cases where subject changes mid-conversation
            body_preview = email['body'][:500] if len(email['body']) > 500 else email['body']

            # Add thread_id to help AI understand these are from different conversations
            thread_id = email.get('thread_id', 'unknown')

            formatted_parts.append(
                f"{i}. From: {email['sender']}\n"
                f"   Subject: {email['subject']}\n"
                f"   Date: {email['date']}\n"
                f"   Thread: {thread_id}\n"
                f"   Body: {body_preview}{'...' if len(email['body']) > 500 else ''}\n"
            )

    return "\n".join(formatted_parts)


def _multilingual_needs_response(email_body: str, subject: str, language: str) -> bool:
    """Multilingual rule-based detection for emails requiring response.

    Uses language-specific question indicators from response_generation.py.
    Supports 4 languages: en, de, ru, uk

    Args:
        email_body: Email body text
        subject: Email subject line
        language: Detected language code (en/de/ru/uk)

    Returns:
        True if email likely needs response, False otherwise

    Example:
        >>> _multilingual_needs_response("Когда ты сможешь прийти?", "Вопрос", "ru")
        True
        >>> _multilingual_needs_response("When can you confirm?", "Meeting", "en")
        True
        >>> _multilingual_needs_response("Thank you for the information", "Re: Meeting", "en")
        False
    """
    import re
    from app.prompts.response_generation import QUESTION_INDICATORS

    text = f"{subject} {email_body}".lower()

    # Get language-specific indicators, fallback to English
    indicators = QUESTION_INDICATORS.get(language, QUESTION_INDICATORS["en"])

    # Check for question indicators with word boundaries
    for indicator in indicators:
        indicator_lower = indicator.lower()

        # Special case: question mark doesn't need word boundaries
        if indicator_lower == "?":
            if "?" in text:
                logger.info(
                    "needs_response_detected",
                    indicator=indicator,
                    language=language
                )
                return True
        else:
            # Use word boundaries to avoid false matches (e.g., "як" in "Дякую")
            # \b matches word boundaries for ASCII letters
            # For Cyrillic/Unicode, we use \s or punctuation as boundaries
            pattern = r'(?:^|\s|[,.!?;:])' + re.escape(indicator_lower) + r'(?:\s|[,.!?;:]|$)'
            if re.search(pattern, text):
                logger.info(
                    "needs_response_detected",
                    indicator=indicator,
                    language=language
                )
                return True

    return False


class EmailClassificationService:
    """Service for classifying emails using AI-powered analysis.

    This service integrates multiple components:
    - Gmail API: Retrieve full email content
    - Database: Load user's folder categories and email metadata
    - Gemini LLM: Classify email into appropriate folder
    - Prompt Engineering: Use optimized classification prompts from Story 2.2

    Attributes:
        db: SQLAlchemy async session for database operations
        gmail_client: Gmail API client for email retrieval
        llm_client: Gemini LLM client for classification
    """

    def __init__(
        self,
        db: AsyncSession,
        gmail_client: GmailClient,
        llm_client: LLMClient,
    ):
        """Initialize classification service with required dependencies.

        Args:
            db: SQLAlchemy async session
            gmail_client: Gmail API client instance
            llm_client: Gemini LLM client instance
        """
        self.db = db
        self.gmail_client = gmail_client
        self.llm_client = llm_client

    def _call_gemini_with_retry(self, prompt: str, operation: str) -> Dict:
        """Call Gemini API with automatic retry for rate limits.

        NOTE: Retry logic is handled by llm_client.send_prompt() to avoid double-retry.
        This wrapper exists for backwards compatibility and logging.

        Args:
            prompt: Classification prompt text
            operation: Operation name for logging ("classification")

        Returns:
            Dict with classification response from Gemini

        Raises:
            GeminiRateLimitError: If rate limit persists after retries
            GeminiAPIError: For other API errors
            GeminiTimeoutError: For timeout errors
        """
        logger.info("calling_gemini", operation=operation)
        return self.llm_client.receive_completion(prompt=prompt, operation=operation)

    @staticmethod
    def _is_automated_sender(sender: str) -> bool:
        """Detect automated/marketing senders that NEVER need response.

        This is a rule-based pre-filter that runs BEFORE calling the LLM to catch
        obvious automated emails (noreply, notifications, newsletters, marketing).

        This prevents LLM from wasting tokens and making incorrect decisions on
        emails that are clearly automated based on sender address patterns.

        Args:
            sender: Email sender address (e.g., "noreply@github.com", "info@company.com")

        Returns:
            True if sender is automated/marketing (no response needed), False otherwise

        Examples:
            >>> _is_automated_sender("noreply@github.com")
            True
            >>> _is_automated_sender("notifications@vercel.com")
            True
            >>> _is_automated_sender("podpiska@company.com")  # Ukrainian "subscription"
            True
            >>> _is_automated_sender("john.doe@company.com")
            False
        """
        sender_lower = sender.lower()

        # CRITICAL STEP 1: Check sender address patterns
        # These patterns indicate automated/bulk emails that should NEVER get response

        # Pattern 1: No-reply addresses
        noreply_patterns = ["noreply@", "no-reply@", "donotreply@", "do-not-reply@"]
        if any(pattern in sender_lower for pattern in noreply_patterns):
            logger.info(
                "automated_sender_detected",
                sender=sender,
                pattern="noreply",
                reason="No-reply address detected"
            )
            return True

        # Pattern 2: Automated notification/alert systems
        notification_patterns = [
            "notifications@", "notification@",
            "alerts@", "alert@",
            "updates@", "update@",
            "automated@", "automation@",
            "system@", "admin@"
        ]
        if any(pattern in sender_lower for pattern in notification_patterns):
            logger.info(
                "automated_sender_detected",
                sender=sender,
                pattern="notifications",
                reason="Automated notification system detected"
            )
            return True

        # Pattern 3: Marketing/Newsletter/Bulk email domains
        marketing_domain_patterns = [
            "@send.", "@email.", "@mail.",
            "@marketing.", "@newsletter.", "@promo.",
            "@campaigns.", "@broadcast."
        ]
        if any(pattern in sender_lower for pattern in marketing_domain_patterns):
            logger.info(
                "automated_sender_detected",
                sender=sender,
                pattern="marketing_domain",
                reason="Marketing/newsletter domain detected"
            )
            return True

        # Pattern 4: Newsletter/subscription sender addresses
        newsletter_patterns = [
            "newsletter@", "newsletters@",
            "podpiska@",  # Ukrainian "subscription"
            "subscribe@", "subscriptions@",
            "digest@", "updates@"
        ]
        if any(pattern in sender_lower for pattern in newsletter_patterns):
            logger.info(
                "automated_sender_detected",
                sender=sender,
                pattern="newsletter",
                reason="Newsletter/subscription address detected"
            )
            return True

        # Pattern 5: Generic marketing sender addresses (info@, contact@, hello@, hi@)
        # These are VERY common for marketing emails
        # NOTE: We're being conservative here - info@ from known personal contacts
        # should still pass through, but for unknown senders it's likely marketing
        generic_marketing_patterns = ["info@", "contact@", "hello@", "hi@", "hey@", "sales@", "support@"]
        if any(pattern in sender_lower for pattern in generic_marketing_patterns):
            # For now, we'll flag these but let LLM make final decision
            # In future, we can make this stricter if we have sender_history showing
            # no previous conversation with this sender
            logger.debug(
                "potential_automated_sender",
                sender=sender,
                pattern="generic_marketing",
                reason="Generic marketing address (info@/contact@/etc.) - flagged but allowing LLM to decide"
            )
            # NOTE: Returning False for now to let LLM analyze sender_history
            # If sender_history shows >5 emails with no responses, LLM should catch it
            return False

        # Not an automated sender based on address patterns
        return False

    async def classify_email(
        self, email_id: int, user_id: int
    ) -> ClassificationResponse:
        """Classify an email into a user-defined folder category using AI.

        This method orchestrates the full classification workflow:
        1. Load email metadata from EmailProcessingQueue
        2. Retrieve full email content from Gmail API
        3. Load user's folder categories from database
        4. Retrieve RAG context (thread history + semantic search)
        5. Construct classification prompt with RAG context using build_classification_prompt()
        6. Call Gemini LLM API for unified classification (folder + needs_response + draft)
        7. Parse and validate JSON response into ClassificationResponse

        Args:
            email_id: EmailProcessingQueue.id of the email to classify
            user_id: User ID who owns the email (for loading folders)

        Returns:
            ClassificationResponse: Parsed classification result with:
                - suggested_folder (str): Folder name for sorting
                - reasoning (str): AI reasoning for classification (max 300 chars)
                - priority_score (int): Priority score 0-100 (optional)
                - confidence (float): Classification confidence 0.0-1.0 (optional)
                - needs_response (bool): Whether email requires response (default: False)
                - response_draft (str): AI-generated draft response if needs_response=True (optional)

        Raises:
            ValueError: If email_id not found or doesn't belong to user_id
            GmailAPIError: If email retrieval from Gmail fails (propagated)
            Exception: Other unexpected errors (logged and re-raised)

        Example:
            >>> service = EmailClassificationService(db, gmail_client, llm_client)
            >>> result = await service.classify_email(email_id=123, user_id=456)
            >>> print(result.suggested_folder)  # "Work"
            >>> print(result.reasoning)  # "Meeting invitation from manager"
        """
        logger.info("classification_started", email_id=email_id, user_id=user_id)

        # Step 1: Load email metadata from database
        result = await self.db.execute(
            select(EmailProcessingQueue).where(
                EmailProcessingQueue.id == email_id,
                EmailProcessingQueue.user_id == user_id,
            )
        )
        email = result.scalar_one_or_none()

        if not email:
            logger.error(
                "email_not_found",
                email_id=email_id,
                user_id=user_id,
            )
            raise ValueError(
                f"Email {email_id} not found or doesn't belong to user {user_id}"
            )

        # Step 2: Retrieve full email content from Gmail
        # This uses the gmail_message_id stored in the database
        # Note: Gmail API errors are propagated - workflow cannot continue without email content
        logger.debug(
            "retrieving_email_from_gmail",
            gmail_message_id=email.gmail_message_id,
        )

        try:
            email_detail = await self.gmail_client.get_message_detail(
                message_id=email.gmail_message_id
            )
        except GmailAPIError as e:
            # Gmail API errors are CRITICAL - propagate exception
            # Workflow cannot continue without email content
            logger.error(
                "gmail_retrieval_failed",
                email_id=email_id,
                gmail_message_id=email.gmail_message_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Load user email separately to avoid lazy-loading in async context
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else ""

        # Extract email data for prompt construction
        email_data = {
            "sender": email_detail["sender"],
            "subject": email_detail["subject"],
            "body": email_detail["body"],
            "user_email": user_email,
        }

        # Step 3: Load user's folder categories from database
        result = await self.db.execute(
            select(FolderCategory).where(FolderCategory.user_id == user_id)
        )
        folders = result.scalars().all()

        if not folders:
            logger.warning(
                "no_folders_found",
                user_id=user_id,
                note="User has no folder categories configured",
            )
            # Return fallback classification if no folders exist
            return ClassificationResponse(
                suggested_folder="Inbox",
                reasoning="No folder categories configured for this user",
                priority_score=50,
                confidence=0.0,
            )

        # Convert folder models to dictionaries for prompt builder
        user_folders = [
            {
                "name": folder.name,
                "description": f"Keywords: {', '.join(folder.keywords)}"
                if folder.keywords
                else "",
            }
            for folder in folders
        ]

        # Step 3.5: PRE-FILTER - Check if sender is automated/marketing (BEFORE calling LLM)
        # This rule-based check catches obvious automated emails and prevents LLM from
        # wasting tokens and making incorrect "needs_response=true" decisions
        is_automated = self._is_automated_sender(email_data["sender"])

        if is_automated:
            logger.info(
                "automated_sender_pre_filter",
                email_id=email_id,
                sender=email_data["sender"],
                action="Skipping LLM call - forcing needs_response=false"
            )
            # Return early with needs_response=false, skip LLM call
            # Still need to determine folder, so we'll use a simple rule or default folder
            return ClassificationResponse(
                suggested_folder=user_folders[0]["name"] if user_folders else "Important",
                reasoning="Automated email (newsletter/notification) - no response needed",
                priority_score=10,  # Low priority for automated emails
                confidence=1.0,  # High confidence in rule-based detection
                needs_response=False,  # CRITICAL: Force false for automated senders
                response_draft=None,
                detected_language="en",  # Will be detected if needed
                tone="professional"
            )

        # Step 4: Retrieve RAG context (thread history + semantic search)
        logger.debug(
            "retrieving_rag_context",
            email_id=email_id,
            gmail_thread_id=email.gmail_thread_id,
        )

        rag_context_formatted = ""
        try:
            # Initialize ContextRetrievalService for this user
            context_retrieval_service = ContextRetrievalService(user_id=user_id)

            # Retrieve context (thread history + semantic search)
            rag_context = await context_retrieval_service.retrieve_context(email_id=email_id)

            # Format RAG context for prompt
            rag_context_formatted = _format_rag_context(rag_context)

            logger.debug(
                "rag_context_retrieved",
                thread_count=len(rag_context.get("thread_history", [])),
                semantic_count=len(rag_context.get("semantic_results", [])),
                total_tokens=rag_context.get("metadata", {}).get("total_tokens_used", 0),
            )
        except Exception as e:
            # RAG retrieval failure is NOT critical - continue with empty context
            logger.warning(
                "rag_retrieval_failed",
                email_id=email_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                note="Continuing classification without RAG context",
            )
            rag_context_formatted = ""

        # Step 5: Construct classification prompt using Story 2.2 prompt builder
        logger.debug(
            "building_classification_prompt",
            folder_count=len(user_folders),
            has_rag_context=bool(rag_context_formatted),
        )

        prompt = build_classification_prompt(
            email_data=email_data,
            user_folders=user_folders,
            rag_context=rag_context_formatted
        )

        # DEBUG: Log complete prompt for sender_history verification
        sender_history_in_prompt = "Full Conversation with Sender" in prompt
        logger.info(
            "classification_prompt_constructed",
            email_id=email_id,
            prompt_length=len(prompt),
            has_sender_history_section=sender_history_in_prompt,
            sender_history_count=len(rag_context.get("sender_history", [])) if 'rag_context' in locals() else 0,
            prompt_preview=prompt[:2000] if len(prompt) > 2000 else prompt,
        )

        # Step 6: Call Groq LLM API with JSON response format
        # NO FALLBACK - Groq is reliable, if errors occur they should be raised and handled by workflow
        logger.debug("calling_groq_llm", operation="classification")

        # Call Groq with automatic retry for transient errors
        llm_response = self._call_gemini_with_retry(
            prompt=prompt, operation="classification"
        )

        # Step 7: Parse JSON response into ClassificationResponse Pydantic model
        # ValidationError will be raised to caller - NO FALLBACK
        try:
            classification = ClassificationResponse(**llm_response)
        except ValidationError as e:
            # Invalid JSON response from LLM - log and re-raise
            logger.error(
                "classification_validation_error",
                email_id=email_id,
                user_id=user_id,
                error_type="ValidationError",
                error=str(e),
                llm_response_preview=str(llm_response)[:500],
                note="Pydantic validation failed on LLM response - re-raising exception",
            )
            # Re-raise to let workflow handle the error
            raise

        logger.info(
            "classification_completed",
            email_id=email_id,
            suggested_folder=classification.suggested_folder,
            priority_score=classification.priority_score,
        )

        return classification

    # DEPRECATED: Fallback logic removed as per user request (2025-12-13)
    # Groq LLM is reliable and doesn't have rate limit issues like Gemini
    # If classification fails, exceptions should be raised to Dead Letter Queue
    #
    # def _create_fallback_classification(
    #     self,
    #     reason: str,
    #     fallback_folder: str = "Important",
    #     email_data: Dict = None
    # ) -> ClassificationResponse:
    #     """Create comprehensive fallback classification using existing services (no LLM calls).
    #
    #     This fallback ensures the workflow can continue even when Gemini API fails.
    #     Uses existing services to detect ALL critical workflow fields:
    #     - LanguageDetectionService for language detection (en/de/ru/uk)
    #     - ToneDetectionService (rule-based only) for tone detection (formal/professional/casual)
    #     - Multilingual QUESTION_INDICATORS for needs_response detection
    #
    #     Args:
    #         reason: Human-readable reason for fallback (e.g., "API timeout", "Rate limit exceeded")
    #         fallback_folder: Folder name to use as fallback (from user's folders)
    #         email_data: Email data dict with 'subject', 'body', 'sender' for comprehensive detection
    #
    #     Returns:
    #         ClassificationResponse with ALL workflow-critical fields:
    #             - suggested_folder: Fallback folder (from user's folders)
    #             - reasoning: Reason for fallback + detected language/tone
    #             - priority_score: 50 (medium priority for manual review)
    #             - confidence: 0.0 (no confidence in fallback classification)
    #             - needs_response: Multilingual rule-based detection
    #             - response_draft: None (no draft available in fallback)
    #             - detected_language: Auto-detected from email body (en/de/ru/uk)
    #             - tone: Rule-based detection from sender domain (formal/professional/casual)
    #     """
    #     # Default values
    #     language = "en"
    #     tone = "professional"
    #     needs_response = False
    #     priority_score = 50
    #
    #     if email_data:
    #         subject = email_data.get("subject", "")
    #         body = email_data.get("body", "")
    #         sender = email_data.get("sender", "")
    #
    #         # 1. Detect language using LanguageDetectionService
    #         try:
    #             from app.services.language_detection import LanguageDetectionService
    #             lang_service = LanguageDetectionService()
    #             language, confidence = lang_service.detect_with_fallback(body, fallback_lang="en")
    #
    #             logger.info(
    #                 "fallback_language_detected",
    #                 language=language,
    #                 confidence=confidence
    #             )
    #         except Exception as e:
    #             logger.error("fallback_language_detection_failed", error=str(e))
    #             language = "en"  # Safe fallback
    #
    #         # 2. Detect tone using rule-based logic (NO LLM calls)
    #         try:
    #             from app.services.tone_detection import ToneDetectionService
    #
    #             # Extract domain from sender email
    #             sender_domain = sender.split("@")[-1] if "@" in sender else ""
    #
    #             # Use GOVERNMENT_DOMAINS constant for formal tone detection
    #             government_domains = {
    #                 "finanzamt.de", "auslaenderbehoerde.de", "bundesagentur.de",
    #                 "arbeitsagentur.de", "tax.gov", "irs.gov"
    #             }
    #
    #             # Rule-based tone detection (NO database queries, NO LLM)
    #             if sender_domain in government_domains:
    #                 tone = "formal"
    #             elif sender_domain and not sender_domain.endswith(("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "web.de", "gmx.de")):
    #                 # Business domain (not free email provider)
    #                 tone = "professional"
    #             else:
    #                 # Personal/free email provider
    #                 tone = "casual"
    #
    #             logger.info("fallback_tone_detected", tone=tone, sender=sender)
    #
    #         except Exception as e:
    #             logger.error("fallback_tone_detection_failed", error=str(e))
    #             tone = "professional"  # Safe fallback
    #
    #         # 3. Detect needs_response using multilingual indicators
    #         needs_response = _multilingual_needs_response(body, subject, language)
    #
    #         logger.info(
    #             "fallback_comprehensive_detection",
    #             language=language,
    #             tone=tone,
    #             needs_response=needs_response,
    #             subject=subject[:100],
    #             body_preview=body[:200]
    #         )
    #
    #     return ClassificationResponse(
    #         suggested_folder=fallback_folder,
    #         reasoning=f"{reason}. Fallback: language={language}, tone={tone}",
    #         priority_score=priority_score,
    #         confidence=0.0,
    #         needs_response=needs_response,
    #         response_draft=None,
    #         detected_language=language,  # ← CRITICAL for workflow!
    #         tone=tone,  # ← CRITICAL for workflow!
    #     )
