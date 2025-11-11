"""Language detection service for email content.

This module provides language detection functionality for incoming emails,
identifying the primary language of email body text to enable appropriate
response generation in the detected language.

Key Features:
- Detects language from email body text using langdetect library
- Supports 4 target languages: Russian (ru), Ukrainian (uk), English (en), German (de)
- Returns confidence scores for language predictions
- Handles mixed-language emails by selecting primary language (highest probability)
- Implements confidence threshold (0.7) with fallback to English for low confidence
- Robust error handling for edge cases (empty text, HTML content, ambiguous text)

Usage:
    from app.services.language_detection import LanguageDetectionService

    # Initialize service
    detector = LanguageDetectionService()

    # Detect language with confidence
    lang_code, confidence = detector.detect("Dies ist ein deutscher Text")
    # Returns: ("de", 0.95)

    # Detect with fallback for low confidence
    lang_code, confidence = detector.detect_with_fallback("Short text")
    # Returns: ("en", 0.0) if confidence < 0.7

    # Check if language is supported
    is_supported = detector.is_supported_language("de")
    # Returns: True

Supported Language Codes:
    - ru: Russian
    - uk: Ukrainian
    - en: English
    - de: German
"""

from typing import List, Tuple

import structlog
from langdetect import LangDetectException, detect_langs

from app.core.preprocessing import strip_html

logger = structlog.get_logger(__name__)


class LanguageDetectionService:
    """Service for detecting language of email content.

    This service uses the langdetect library to identify the primary language
    of email body text. It supports 4 target languages and implements confidence
    threshold logic with fallback to English for ambiguous cases.

    Attributes:
        SUPPORTED_LANGUAGES: List of supported 2-letter language codes
        CONFIDENCE_THRESHOLD: Minimum confidence (0.7) for accepting detection
    """

    # Supported languages (AC #3)
    SUPPORTED_LANGUAGES = ["ru", "uk", "en", "de"]

    # Confidence threshold for fallback logic (AC #8)
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self) -> None:
        """Initialize the LanguageDetectionService.

        Sets up logging and initializes the service for language detection.
        """
        self.logger = logger.bind(service="language_detection")
        self.logger.info("LanguageDetectionService initialized",
                        supported_languages=self.SUPPORTED_LANGUAGES,
                        confidence_threshold=self.CONFIDENCE_THRESHOLD)

    def detect(self, email_body: str) -> Tuple[str, float]:
        """Detect primary language from email body text.

        Analyzes the email body content and returns the detected language code
        with confidence score. Uses langdetect library for detection.

        Args:
            email_body: Email body text to analyze (plain text or HTML)

        Returns:
            Tuple of (language_code, confidence) where:
                - language_code: 2-letter ISO language code (e.g., "de", "ru")
                - confidence: Float between 0.0 and 1.0 indicating detection confidence

        Raises:
            ValueError: If email_body is empty or None
            LangDetectException: If language detection fails due to ambiguous text

        Example:
            >>> detector = LanguageDetectionService()
            >>> lang, conf = detector.detect("Dies ist ein deutscher Text")
            >>> print(f"{lang}: {conf:.2f}")
            de: 0.95
        """
        # Validate input
        if not email_body or not email_body.strip():
            self.logger.warning("Empty email body provided for language detection")
            raise ValueError("Email body cannot be empty")

        # Strip HTML tags if present
        clean_text = strip_html(email_body) if "<" in email_body else email_body
        clean_text = clean_text.strip()

        # Check for very short text
        if len(clean_text) < 20:
            self.logger.warning(
                "Very short text for language detection",
                text_length=len(clean_text),
                preview=clean_text[:50]
            )

        # Get email preview for logging (first 50 chars)
        email_preview = clean_text[:50].replace("\n", " ")

        try:
            # Detect language with probabilities
            langs = detect_langs(clean_text)

            if not langs:
                self.logger.error("No languages detected", preview=email_preview)
                raise LangDetectException("No languages detected")

            # Get primary language (highest probability)
            primary_lang = langs[0]
            lang_code = primary_lang.lang.lower()  # Normalize to lowercase
            confidence = primary_lang.prob

            self.logger.info(
                "Language detected",
                preview=email_preview,
                detected_language=lang_code,
                confidence=round(confidence, 3),
                text_length=len(clean_text)
            )

            return (lang_code, confidence)

        except LangDetectException as e:
            self.logger.error(
                "Language detection failed",
                preview=email_preview,
                error=str(e),
                text_length=len(clean_text)
            )
            raise

    def is_supported_language(self, lang_code: str) -> bool:
        """Check if a language code is in the supported languages list.

        Args:
            lang_code: 2-letter language code to check (e.g., "de", "ru")

        Returns:
            True if language is supported, False otherwise

        Example:
            >>> detector = LanguageDetectionService()
            >>> detector.is_supported_language("de")
            True
            >>> detector.is_supported_language("fr")
            False
        """
        # Normalize to lowercase for comparison
        normalized_code = lang_code.lower() if lang_code else ""
        is_supported = normalized_code in self.SUPPORTED_LANGUAGES

        if not is_supported and lang_code:
            self.logger.debug(
                "Language code not in supported list",
                language_code=lang_code,
                supported_languages=self.SUPPORTED_LANGUAGES
            )

        return is_supported

    def detect_primary_language(self, email_body: str) -> str:
        """Detect primary language from potentially mixed-language email.

        For emails containing multiple languages, returns the language with
        the highest probability (primary language). Logs all detected languages
        with their probabilities if multiple are found.

        Args:
            email_body: Email body text to analyze (may contain multiple languages)

        Returns:
            Primary language code (highest probability) as 2-letter ISO code

        Example:
            >>> detector = LanguageDetectionService()
            >>> # Email with 70% German, 20% English, 10% Russian
            >>> primary = detector.detect_primary_language(mixed_email)
            >>> print(primary)
            de
        """
        # Strip HTML if present
        clean_text = strip_html(email_body) if "<" in email_body else email_body
        clean_text = clean_text.strip()

        # Get email preview for logging
        email_preview = clean_text[:50].replace("\n", " ")

        try:
            # Detect all languages with probabilities
            langs = detect_langs(clean_text)

            if not langs:
                self.logger.warning("No languages detected, defaulting to English", preview=email_preview)
                return "en"

            # Sort by probability descending (already sorted by langdetect, but explicit for clarity)
            sorted_langs = sorted(langs, key=lambda x: x.prob, reverse=True)

            # Get primary language (highest probability)
            primary_lang = sorted_langs[0]
            primary_code = primary_lang.lang.lower()

            # Log all detected languages if multiple found
            if len(sorted_langs) > 1:
                lang_probabilities = [
                    f"{lang.lang.lower()}:{round(lang.prob, 2)}"
                    for lang in sorted_langs
                ]
                self.logger.info(
                    "Mixed-language email detected",
                    preview=email_preview,
                    primary_language=primary_code,
                    all_languages=", ".join(lang_probabilities)
                )
            else:
                self.logger.info(
                    "Single language detected",
                    preview=email_preview,
                    language=primary_code,
                    confidence=round(primary_lang.prob, 3)
                )

            return primary_code

        except LangDetectException as e:
            self.logger.error(
                "Language detection failed in detect_primary_language",
                preview=email_preview,
                error=str(e)
            )
            # Return English as fallback
            return "en"

    def detect_with_fallback(self, email_body: str, fallback_lang: str = "en") -> Tuple[str, float]:
        """Detect language with confidence threshold and fallback logic.

        Detects language and applies confidence threshold (0.7). If confidence
        is below threshold, returns fallback language (default: English).

        Args:
            email_body: Email body text to analyze
            fallback_lang: Language code to use if confidence < threshold (default: "en")

        Returns:
            Tuple of (language_code, confidence) where language_code may be
            fallback_lang if primary detection confidence was too low

        Example:
            >>> detector = LanguageDetectionService()
            >>> # Ambiguous short text
            >>> lang, conf = detector.detect_with_fallback("OK thx")
            >>> print(f"{lang}: {conf:.2f}")
            en: 0.45  # Fallback to English applied
        """
        try:
            # Detect language using primary detection method
            detected_lang, confidence = self.detect(email_body)

            # Check if detected language is supported
            if not self.is_supported_language(detected_lang):
                self.logger.info(
                    "Unsupported language detected, applying fallback",
                    original_detection=detected_lang,
                    confidence=round(confidence, 3),
                    fallback_language=fallback_lang
                )
                return (fallback_lang, confidence)

            # Apply confidence threshold
            if confidence < self.CONFIDENCE_THRESHOLD:
                self.logger.info(
                    "Low confidence detection, applying fallback",
                    original_detection=detected_lang,
                    confidence=round(confidence, 3),
                    threshold=self.CONFIDENCE_THRESHOLD,
                    fallback_language=fallback_lang
                )
                return (fallback_lang, confidence)

            # Confidence above threshold and language supported - return detected language
            return (detected_lang, confidence)

        except (ValueError, LangDetectException) as e:
            # If detection fails completely, use fallback
            self.logger.warning(
                "Detection failed, using fallback language",
                error=str(e),
                fallback_language=fallback_lang
            )
            return (fallback_lang, 0.0)
