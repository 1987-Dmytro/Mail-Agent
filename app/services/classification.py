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
from typing import Dict
from pydantic import ValidationError

from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient
from app.models.classification_response import ClassificationResponse
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.prompts.classification_prompt import build_classification_prompt
from app.utils.errors import (
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GmailAPIError,
)


logger = structlog.get_logger(__name__)


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

    async def classify_email(
        self, email_id: int, user_id: int
    ) -> ClassificationResponse:
        """Classify an email into a user-defined folder category using AI.

        This method orchestrates the full classification workflow:
        1. Load email metadata from EmailProcessingQueue
        2. Retrieve full email content from Gmail API
        3. Load user's folder categories from database
        4. Construct classification prompt using build_classification_prompt()
        5. Call Gemini LLM API for classification
        6. Parse and validate JSON response into ClassificationResponse

        Args:
            email_id: EmailProcessingQueue.id of the email to classify
            user_id: User ID who owns the email (for loading folders)

        Returns:
            ClassificationResponse: Parsed classification result with:
                - suggested_folder (str): Folder name for sorting
                - reasoning (str): AI reasoning for classification (max 300 chars)
                - priority_score (int): Priority score 0-100 (optional)
                - confidence (float): Classification confidence 0.0-1.0 (optional)

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

        # Step 4: Construct classification prompt using Story 2.2 prompt builder
        logger.debug(
            "building_classification_prompt",
            folder_count=len(user_folders),
        )

        prompt = build_classification_prompt(
            email_data=email_data, user_folders=user_folders
        )

        # Step 5: Call Gemini LLM API with JSON response format
        # Gemini API errors trigger fallback to "Unclassified" - workflow continues
        logger.debug("calling_gemini_llm", operation="classification")

        try:
            # receive_completion is synchronous - do NOT await
            llm_response = self.llm_client.receive_completion(
                prompt=prompt, operation="classification"
            )

            # Step 6: Parse JSON response into ClassificationResponse Pydantic model
            # Pydantic ValidationError triggers fallback to "Unclassified"
            try:
                classification = ClassificationResponse(**llm_response)
            except ValidationError as e:
                # Invalid JSON response from Gemini - use fallback classification
                # Use first user folder as fallback
                fallback_folder = user_folders[0]["name"] if user_folders else "Important"
                logger.warning(
                    "classification_fallback",
                    email_id=email_id,
                    user_id=user_id,
                    error_type="ValidationError",
                    error=str(e),
                    fallback_folder=fallback_folder,
                    note="Pydantic validation failed on LLM response",
                )
                return self._create_fallback_classification(
                    "Classification failed: Invalid response format from AI",
                    fallback_folder=fallback_folder,
                )

        except (GeminiAPIError, GeminiRateLimitError, GeminiTimeoutError) as e:
            # Gemini API errors (rate limits, timeouts, API errors) - use fallback
            # Use first user folder as fallback
            fallback_folder = user_folders[0]["name"] if user_folders else "Important"
            logger.warning(
                "classification_fallback",
                email_id=email_id,
                user_id=user_id,
                error_type=type(e).__name__,
                error=str(e),
                fallback_folder=fallback_folder,
                note="Gemini API error, workflow continues with fallback",
            )
            return self._create_fallback_classification(
                f"Classification failed due to {type(e).__name__}",
                fallback_folder=fallback_folder,
            )

        logger.info(
            "classification_completed",
            email_id=email_id,
            suggested_folder=classification.suggested_folder,
            priority_score=classification.priority_score,
        )

        return classification

    def _create_fallback_classification(
        self, reason: str, fallback_folder: str = "Important"
    ) -> ClassificationResponse:
        """Create fallback classification response when AI classification fails.

        This fallback ensures the workflow can continue even when Gemini API fails.
        The email is marked with the first available user folder (or "Important")
        with medium priority for manual review.

        Args:
            reason: Human-readable reason for fallback (e.g., "API timeout")
            fallback_folder: Folder name to use as fallback (from user's folders)

        Returns:
            ClassificationResponse with fallback values:
                - suggested_folder: First user folder or "Important"
                - reasoning: Reason for fallback
                - priority_score: 50 (medium priority for manual review)
                - confidence: 0.0 (no confidence in fallback classification)
        """
        return ClassificationResponse(
            suggested_folder=fallback_folder,
            reasoning=reason[:300],  # Truncate to max 300 chars
            priority_score=50,  # Medium priority for manual review
            confidence=0.0,  # No confidence in fallback classification
        )
