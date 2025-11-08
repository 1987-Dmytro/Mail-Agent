"""Priority email detection service.

This service analyzes email metadata (sender, subject, body) to determine if an email
requires immediate notification, bypassing batch processing. Uses a weighted scoring
algorithm based on government domains, urgency keywords, and user configuration.

Priority Scoring:
- Government domain match: +50 points
- Urgency keyword match: +30 points
- User-configured priority sender: +40 points
- Maximum score: 100 (capped)
- Priority threshold: 70 (default, configurable)

Usage:
    service = PriorityDetectionService(db_session)
    result = await service.detect_priority(
        email_id=123,
        sender="finanzamt@berlin.de",
        subject="Wichtig: Deadline approaching",
        body_preview="..."
    )
    # Returns: {"priority_score": 80, "is_priority": True, "detection_reasons": [...]}
"""

import re
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, List, Tuple, Any

from app.config.priority_config import (
    GOVERNMENT_DOMAINS,
    PRIORITY_KEYWORDS,
    PRIORITY_THRESHOLD,
)
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory


logger = structlog.get_logger(__name__)


class PriorityDetectionService:
    """Service for detecting high-priority emails requiring immediate notification.

    This service implements a multi-factor priority scoring algorithm that analyzes
    email sender, subject, and content to determine if immediate notification is needed.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession):
        """Initialize priority detection service.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def detect_priority(
        self,
        email_id: int,
        sender: str,
        subject: str,
        body_preview: str = "",
    ) -> Dict[str, Any]:
        """Analyze email to determine priority level.

        Implements multi-factor scoring algorithm:
        1. Check government sender domain (+50 if match)
        2. Check urgency keywords in subject/body (+30 if match)
        3. Check user-configured priority senders (+40 if match)
        4. Cap total score at 100
        5. Mark as priority if score >= PRIORITY_THRESHOLD

        Args:
            email_id: EmailProcessingQueue.id of the email
            sender: Email sender address (e.g., "name@domain.de" or "Name <name@domain.de>")
            subject: Email subject line
            body_preview: Email body preview (first ~200 characters)

        Returns:
            Dict with:
                - priority_score (int): 0-100 priority score
                - is_priority (bool): True if score >= threshold
                - detection_reasons (List[str]): List of detection triggers
                  (e.g., ["government_domain:finanzamt.de", "keyword:wichtig"])

        Example:
            >>> service = PriorityDetectionService(db)
            >>> result = await service.detect_priority(
            ...     email_id=123,
            ...     sender="finanzamt@berlin.de",
            ...     subject="Wichtig: Steuerfrist 15.12.2024",
            ...     body_preview="..."
            ... )
            >>> result["priority_score"]  # 80
            >>> result["is_priority"]  # True
            >>> result["detection_reasons"]  # ["government_domain:finanzamt.de", "keyword:wichtig"]
        """
        priority_score = 0
        detection_reasons = []

        # Check government domain (+50 points)
        if self._is_government_sender(sender):
            priority_score += 50
            domain = self._extract_domain(sender)
            detection_reasons.append(f"government_domain:{domain}")

        # Check urgency keywords (+30 points)
        keyword_score, keywords_found = self._check_urgency_keywords(subject, body_preview)
        priority_score += keyword_score
        if keywords_found:
            detection_reasons.extend([f"keyword:{kw}" for kw in keywords_found])

        # Check user-configured priority senders (+40 points)
        user_config_score = await self._check_user_priority_senders(email_id, sender)
        priority_score += user_config_score
        if user_config_score > 0:
            detection_reasons.append(f"user_configured_sender:{sender}")

        # Cap score at 100
        priority_score = min(priority_score, 100)

        # Determine if priority based on threshold
        is_priority = priority_score >= PRIORITY_THRESHOLD

        # Log detection
        logger.info(
            "priority_detection_completed",
            email_id=email_id,
            sender=sender,
            priority_score=priority_score,
            is_priority=is_priority,
            detection_reasons=detection_reasons,
        )

        return {
            "priority_score": priority_score,
            "is_priority": is_priority,
            "detection_reasons": detection_reasons,
        }

    def _is_government_sender(self, sender: str) -> bool:
        """Check if sender email address is from a government domain.

        Args:
            sender: Email sender address (e.g., "name@domain.de" or "Name <name@domain.de>")

        Returns:
            True if sender domain matches any configured government domain
        """
        domain = self._extract_domain(sender)
        return domain in GOVERNMENT_DOMAINS

    def _check_urgency_keywords(
        self, subject: str, body: str
    ) -> Tuple[int, List[str]]:
        """Check for urgency keywords in email subject and body.

        Searches for multilingual urgency keywords (EN, DE, RU, UK) in both
        subject and body preview. Case-insensitive matching.

        Args:
            subject: Email subject line
            body: Email body preview

        Returns:
            Tuple of (score: int, keywords_found: List[str])
            - score: 30 if any keyword found, else 0
            - keywords_found: List of matched keywords (lowercase)
        """
        # Combine subject and body for analysis
        text_to_analyze = f"{subject} {body}".lower()

        # Search for keywords across all languages
        keywords_found = []
        for language, keywords in PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_to_analyze:
                    keywords_found.append(keyword.lower())

        # Return score and unique keywords found
        if keywords_found:
            return (30, list(set(keywords_found)))
        else:
            return (0, [])

    async def _check_user_priority_senders(
        self, email_id: int, sender: str
    ) -> int:
        """Check if sender is configured as priority by user.

        Queries FolderCategory table for user's priority sender configurations.
        Matches sender address against configured patterns.

        Args:
            email_id: EmailProcessingQueue.id to retrieve user_id
            sender: Email sender address

        Returns:
            40 if sender matches user-configured priority sender, else 0
        """
        try:
            # Get user_id from EmailProcessingQueue
            stmt = select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
            result = await self.db.execute(stmt)
            email_queue = result.scalar_one_or_none()

            if not email_queue:
                logger.warning(
                    "email_not_found_for_priority_check",
                    email_id=email_id,
                )
                return 0

            user_id = email_queue.user_id

            # Query FolderCategories with is_priority_sender flag
            # Note: is_priority_sender field will be added in Task 6
            stmt = select(FolderCategory).where(
                FolderCategory.user_id == user_id,
                FolderCategory.is_priority_sender == True,  # noqa: E712
            )
            result = await self.db.execute(stmt)
            priority_categories = result.scalars().all()

            # Check if sender matches any priority category keywords
            sender_lower = sender.lower()
            for category in priority_categories:
                # Match sender against category keywords
                for keyword in category.keywords:
                    if keyword.lower() in sender_lower:
                        return 40

            return 0

        except Exception as e:
            logger.error(
                "error_checking_user_priority_senders",
                email_id=email_id,
                sender=sender,
                error=str(e),
            )
            return 0

    def _extract_domain(self, sender: str) -> str:
        """Extract domain from email address.

        Handles multiple email address formats:
        - "email@domain.de"
        - "Name <email@domain.de>"
        - "name@subdomain.domain.de"

        Args:
            sender: Email sender address

        Returns:
            Domain part (e.g., "finanzamt.de")
        """
        # Use regex to extract email address from "Name <email@domain>" format
        email_pattern = r"<([^>]+)>|([^\s<>]+@[^\s<>]+)"
        match = re.search(email_pattern, sender)

        if match:
            email = match.group(1) or match.group(2)
            # Extract domain after @
            if "@" in email:
                domain = email.split("@")[1].strip()
                return domain

        return ""
