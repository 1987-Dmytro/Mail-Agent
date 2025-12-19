"""Tone detection service for email response generation.

This service implements hybrid tone detection combining rule-based classification
for known cases (80% coverage) with LLM-based analysis for ambiguous emails (20% cases).

Tone Categories:
- formal: Government correspondence, official bureaucracy (Finanzamt, Ausländerbehörde)
- professional: Business communication, known clients
- casual: Personal correspondence, friends and family

Architecture Decision: ADR-014 - Hybrid approach balances speed (rules), accuracy (known cases),
and flexibility (LLM for edge cases) without incurring API costs for majority of emails.
"""

import structlog
from typing import List, Optional
import google.generativeai as genai

from app.models.email import EmailProcessingQueue
from app.core.config import settings


logger = structlog.get_logger(__name__)


# Government domains requiring formal tone
GOVERNMENT_DOMAINS: List[str] = [
    "finanzamt.de",
    "auslaenderbehoerde.de",
    "bundesagentur-fuer-arbeit.de",
    "stadt.de",
    "gov.de",
    "buergeramt.de",
    "arbeitsagentur.de",
]


class ToneDetectionService:
    """Service for detecting appropriate email response tone.

    Implements hybrid detection strategy:
    1. Rule-based for known cases (government, business, personal)
    2. LLM-based analysis for ambiguous emails
    3. Fallback to "professional" if uncertain

    Attributes:
        gemini_model: Configured Gemini model for LLM-based tone detection
    """

    def __init__(self) -> None:
        """Initialize tone detection service with Gemini API configuration."""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("tone_detection_service_initialized", model="gemini-1.5-flash")
        except Exception as e:
            logger.error("tone_detection_service_init_failed", error=str(e))
            self.gemini_model = None

    def detect_tone(
        self, email: EmailProcessingQueue, thread_history: Optional[List[EmailProcessingQueue]] = None
    ) -> str:
        """Detect appropriate response tone for an email.

        Uses hybrid approach:
        - Rule-based for government domains → "formal"
        - Rule-based for casual greetings/content → "casual" (NEW)
        - Rule-based for known business clients → "professional"
        - Rule-based for personal contacts → "casual"
        - LLM-based for ambiguous cases
        - Fallback to "professional" if uncertain

        Args:
            email: Email object to analyze
            thread_history: Optional list of previous emails in thread for context

        Returns:
            Detected tone: "formal", "professional", or "casual"

        Examples:
            >>> service = ToneDetectionService()
            >>> tone = service.detect_tone(email, thread_history=[])
            >>> print(tone)  # "formal", "professional", or "casual"
        """
        sender_email = email.sender.lower()
        sender_domain = self._extract_domain(sender_email)

        # Log tone detection attempt (without email content for privacy)
        logger.info(
            "tone_detection_started",
            sender=sender_email[:50],  # Truncate for privacy
            has_thread_history=bool(thread_history),
        )

        # Rule 0: Check email content for casual indicators (HIGHEST PRIORITY)
        # This runs BEFORE domain checks because content is more reliable than domain
        if self._has_casual_content(email):
            logger.info(
                "tone_detected_via_rule",
                method="casual_content_detected",
                tone="casual",
            )
            return "casual"

        # Rule 1: Government domains → formal
        if self._is_government_domain(sender_domain):
            logger.info(
                "tone_detected_via_rule",
                method="government_domain",
                domain=sender_domain,
                tone="formal",
            )
            return "formal"

        # Rule 2: Known business clients → professional
        # (In production, this would check against FolderCategories database)
        if self._is_business_client(sender_email):
            logger.info(
                "tone_detected_via_rule",
                method="business_client",
                sender=sender_email[:50],
                tone="professional",
            )
            return "professional"

        # Rule 3: Personal contacts → casual
        # (In production, this would check user's contacts or previous casual threads)
        if self._is_personal_contact(sender_email, thread_history):
            logger.info(
                "tone_detected_via_rule",
                method="personal_contact",
                sender=sender_email[:50],
                tone="casual",
            )
            return "casual"

        # Rule 4: Ambiguous cases → LLM analysis
        if self.gemini_model:
            try:
                llm_tone = self._detect_tone_with_llm(email, thread_history)
                logger.info(
                    "tone_detected_via_llm",
                    sender=sender_email[:50],
                    tone=llm_tone,
                )
                return llm_tone
            except Exception as e:
                logger.warning(
                    "tone_detection_llm_failed",
                    error=str(e),
                    fallback="professional",
                )

        # Fallback: Default to professional
        logger.info(
            "tone_detection_fallback",
            sender=sender_email[:50],
            tone="professional",
            reason="no_rule_match_and_llm_unavailable",
        )
        return "professional"

    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address.

        Args:
            email: Email address string

        Returns:
            Domain part of email address, or empty string if invalid
        """
        if "@" in email:
            return email.split("@")[1].lower()
        return ""

    def _is_government_domain(self, domain: str) -> bool:
        """Check if domain is a known government domain.

        Args:
            domain: Email domain to check

        Returns:
            True if domain matches government patterns
        """
        return any(
            domain.endswith(gov_domain) or domain == gov_domain
            for gov_domain in GOVERNMENT_DOMAINS
        )

    def _is_business_client(self, sender_email: str) -> bool:
        """Check if sender is a known business client.

        In production, this would query the FolderCategories database to check
        if the sender is associated with business-category folders.

        Args:
            sender_email: Sender's email address

        Returns:
            True if sender is a known business contact
        """
        # TODO: Integrate with FolderCategories database in Story 3.7
        # For now, simple heuristic: corporate domains (not free email providers)
        free_email_providers = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "mail.ru"]
        domain = self._extract_domain(sender_email)

        # If it's not a free email provider and not government, likely business
        is_free_provider = any(domain.endswith(provider) for provider in free_email_providers)
        is_government = self._is_government_domain(domain)

        return not is_free_provider and not is_government and domain != ""

    def _is_personal_contact(
        self, sender_email: str, thread_history: Optional[List[EmailProcessingQueue]]
    ) -> bool:
        """Check if sender is a personal contact.

        In production, this would check:
        - User's contacts database
        - Previous threads with casual tone
        - Free email provider + informal subject lines

        Args:
            sender_email: Sender's email address
            thread_history: Previous emails in thread

        Returns:
            True if sender appears to be a personal contact
        """
        # TODO: Integrate with contacts database in future story
        # For now, simple heuristic: free email providers might be personal
        free_email_providers = [
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "mail.ru",
            "keemail.me", "tuta.com", "proton.me", "protonmail.com"  # Privacy-focused personal email
        ]
        domain = self._extract_domain(sender_email)

        return any(domain.endswith(provider) for provider in free_email_providers)

    def _has_casual_content(self, email: EmailProcessingQueue) -> bool:
        """Check if email content contains casual/informal indicators.

        This is the MOST RELIABLE indicator of tone - analyzes actual content
        instead of just domain. Checks for:
        - Informal greetings (Привет, Хай, Hi, Hey, Hallo)
        - Informal addressing (ты, тебя, твой vs Вы, Вас, Ваш)
        - Casual topics (ДР, день рождения, birthday, party)
        - Emojis or casual punctuation (!!!, ???)

        Args:
            email: Email object to analyze

        Returns:
            True if email contains casual indicators
        """
        # Combine subject + body for analysis (first 500 chars)
        content = f"{email.subject} {email.body[:500]}".lower()

        # Casual greetings - multilingual
        casual_greetings = [
            # Russian
            "привет", "приветик", "здорово", "здравствуй", "хай", "салют",
            # Ukrainian
            "привіт", "вітаю", "здоров",
            # English
            "hi ", "hey", "hello there", "yo ", "sup ",
            # German
            "hallo", "hi ", "hey", "moin", "servus",
        ]

        # Informal addressing - "ты" form (Russian/Ukrainian)
        informal_pronouns = [
            # Russian ты-form
            " ты ", " тебя", " тебе", " тобой", " твой", " твоя", " твоё", " твои",
            " приглашаю тебя", " спрошу тебя", " благодарю тебя",
            # Ukrainian ти-form
            " ти ", " тебе", " тобі", " твій", " твоя", " твоє", " твої",
        ]

        # Casual topics/keywords
        casual_topics = [
            "др ", "день рождения", "днюха", "birthday", "party", "вечеринка",
            "встреча", "пиво", "кофе", "coffee", "beer", "hang out",
        ]

        # Check for casual greetings
        if any(greeting in content for greeting in casual_greetings):
            logger.debug("casual_content_detected", reason="casual_greeting")
            return True

        # Check for informal pronouns
        if any(pronoun in content for pronoun in informal_pronouns):
            logger.debug("casual_content_detected", reason="informal_pronoun")
            return True

        # Check for casual topics
        if any(topic in content for topic in casual_topics):
            logger.debug("casual_content_detected", reason="casual_topic")
            return True

        # Check for emojis or excessive punctuation
        if "😊" in content or "!!!" in content or "???" in content:
            logger.debug("casual_content_detected", reason="emojis_or_punctuation")
            return True

        return False

    def _detect_tone_with_llm(
        self, email: EmailProcessingQueue, thread_history: Optional[List[EmailProcessingQueue]]
    ) -> str:
        """Use LLM to detect tone for ambiguous cases.

        Args:
            email: Email to analyze
            thread_history: Previous emails in thread for context

        Returns:
            Detected tone: "formal", "professional", or "casual"

        Raises:
            Exception: If LLM analysis fails
        """
        # Build context from thread history
        thread_context = ""
        if thread_history:
            thread_context = "\n\nPrevious emails in thread:\n"
            for i, prev_email in enumerate(thread_history[-3:], 1):  # Last 3 emails
                thread_context += f"{i}. From: {prev_email.sender}\n   Subject: {prev_email.subject}\n   Body: {prev_email.body[:200]}...\n\n"

        # Construct LLM prompt for tone detection
        prompt = f"""Analyze the following email and determine the appropriate response tone.

CRITICAL: Pay attention to the greeting and how the sender addresses you:
- Informal greetings (Привет, Хай, Hi, Hey) → casual
- Informal addressing (ты, тебя instead of Вы, Вас) → casual
- Personal topics (birthday, party, meeting friends) → casual
- Formal greetings (Здравствуйте, Уважаемый) → formal
- Formal addressing (Вы, Вас, Ваш) → professional/formal

Current Email:
From: {email.sender}
Subject: {email.subject}
Body: {email.body[:500]}...
{thread_context}

Respond with ONLY ONE WORD - the appropriate tone level:
- "formal" for government, legal, or official correspondence
- "professional" for business communication
- "casual" for personal, friendly emails (friends, family, informal invitations)

Response (one word only):"""

        try:
            response = self.gemini_model.generate_content(prompt)
            detected_tone = response.text.strip().lower()

            # Validate response
            if detected_tone in ["formal", "professional", "casual"]:
                return detected_tone
            else:
                logger.warning(
                    "tone_detection_llm_invalid_response",
                    response=detected_tone,
                    fallback="professional",
                )
                return "professional"

        except Exception as e:
            logger.error("tone_detection_llm_error", error=str(e))
            raise
