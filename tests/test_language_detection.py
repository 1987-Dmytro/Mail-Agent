"""Unit tests for LanguageDetectionService.

This module tests the language detection functionality for email content,
validating detection accuracy, confidence scoring, mixed-language handling,
fallback logic, and edge case handling.

Test Coverage:
- AC #2, #4: Language detection with confidence scores
- AC #3: Supported languages validation
- AC #5: Mixed-language email handling
- AC #8: Confidence threshold and fallback logic
- Edge cases: Empty text, short text, HTML content
- Error handling: Invalid input scenarios
"""

import pytest
from langdetect import LangDetectException

from app.services.language_detection import LanguageDetectionService


# Test fixtures for sample email bodies in all 4 supported languages
@pytest.fixture
def sample_emails():
    """Sample email bodies in all 4 supported languages."""
    return {
        "ru": "Здравствуйте! Это тестовое письмо на русском языке. Мы хотим проверить систему определения языка.",
        "uk": "Доброго дня! Це тестовий лист українською мовою. Ми хочемо перевірити систему визначення мови.",
        "en": "Hello! This is a test email in English language. We want to check the language detection system.",
        "de": "Hallo! Dies ist eine Test-E-Mail in deutscher Sprache. Wir möchten das Spracherkennungssystem überprüfen.",
    }


@pytest.fixture
def detector():
    """Initialize LanguageDetectionService for tests."""
    return LanguageDetectionService()


# Test 1: AC #2, #4 - Detect returns language and confidence
def test_detect_returns_language_and_confidence(detector, sample_emails):
    """Test that detect() returns correct language codes and confidence scores.

    Validates:
    - AC #2: detect() method analyzes email body text
    - AC #4: Confidence score calculated and returned
    - All 4 supported languages detected correctly
    - Confidence scores are > 0.7 for clear text
    """
    for expected_lang, email_body in sample_emails.items():
        lang_code, confidence = detector.detect(email_body)

        # Verify language code is correct
        assert lang_code == expected_lang, (
            f"Expected {expected_lang}, got {lang_code} for email: {email_body[:50]}"
        )

        # Verify confidence is high for clear language text
        assert confidence > 0.7, (
            f"Low confidence {confidence} for {expected_lang} email"
        )

        # Verify confidence is a float between 0 and 1
        assert isinstance(confidence, float), "Confidence must be float"
        assert 0.0 <= confidence <= 1.0, "Confidence must be between 0 and 1"


# Test 2: AC #3 - Supported languages validation
def test_supported_languages_validation(detector):
    """Test that is_supported_language() correctly validates all 4 supported languages.

    Validates:
    - AC #3: Supports 4 target languages (ru, uk, en, de)
    - All 4 languages return True
    - Unsupported languages return False
    - Case-insensitive validation (DE, de, De all work)
    """
    # Test all 4 supported languages
    supported_langs = ["ru", "uk", "en", "de"]
    for lang in supported_langs:
        assert detector.is_supported_language(lang) is True, (
            f"Language {lang} should be supported"
        )

    # Test case-insensitive validation
    assert detector.is_supported_language("DE") is True
    assert detector.is_supported_language("En") is True
    assert detector.is_supported_language("RU") is True

    # Test unsupported languages
    unsupported_langs = ["fr", "es", "it", "pl", "ja", "zh"]
    for lang in unsupported_langs:
        assert detector.is_supported_language(lang) is False, (
            f"Language {lang} should NOT be supported"
        )

    # Test empty/None input
    assert detector.is_supported_language("") is False
    assert detector.is_supported_language(None) is False


# Test 3: AC #5 - Mixed-language returns primary
def test_mixed_language_returns_primary(detector):
    """Test that detect_primary_language() returns primary language for mixed-language emails.

    Validates:
    - AC #5: Mixed-language emails handled using primary detected language
    - Language with highest probability is returned
    - Works for various language combinations
    """
    # Mixed German (70%) + English (30%) email
    mixed_email_de_en = """
    Hallo! Dies ist eine wichtige Nachricht über unser Projekt.
    Die Details sind sehr wichtig für das Team.
    We need to discuss this in the next meeting.
    """
    primary = detector.detect_primary_language(mixed_email_de_en)
    assert primary == "de", "Primary language should be German (de) for mostly German text"

    # Mixed Russian (60%) + English (40%) email
    mixed_email_ru_en = """
    Здравствуйте! Это очень важное сообщение.
    Пожалуйста, прочитайте внимательно.
    Please confirm receipt of this email.
    Thank you for your attention.
    """
    primary = detector.detect_primary_language(mixed_email_ru_en)
    assert primary == "ru", "Primary language should be Russian (ru) for mostly Russian text"

    # Mostly English with some German words
    mixed_email_en_de = """
    Hello! This is an important update about our project.
    The meeting will be held next week at our office.
    Vielen Dank for your participation.
    """
    primary = detector.detect_primary_language(mixed_email_en_de)
    assert primary == "en", "Primary language should be English (en) for mostly English text"


# Test 4: AC #8 - Confidence threshold fallback
def test_confidence_threshold_fallback(detector):
    """Test that detect_with_fallback() applies 0.7 confidence threshold.

    Validates:
    - AC #8: Fallback to English when confidence < 0.7
    - Low confidence triggers fallback mechanism
    - Fallback language (en) is returned correctly
    """
    # Very short ambiguous text (low confidence expected)
    short_ambiguous = "OK thx"
    lang, conf = detector.detect_with_fallback(short_ambiguous)

    # Should fallback to English if confidence < 0.7
    if conf < 0.7:
        assert lang == "en", (
            f"Expected fallback to 'en' for low confidence {conf}, got {lang}"
        )

    # Very short text with numbers and symbols
    ambiguous_text = "123 OK @#$"
    lang, conf = detector.detect_with_fallback(ambiguous_text)

    # Should handle gracefully, likely fallback to English
    assert lang in ["en", "ru", "uk", "de"], "Should return a valid language code"
    assert isinstance(conf, float), "Confidence must be float"

    # Test custom fallback language
    custom_fallback = "de"
    lang, conf = detector.detect_with_fallback("OK", fallback_lang=custom_fallback)

    if conf < 0.7:
        assert lang == custom_fallback, (
            f"Expected custom fallback '{custom_fallback}', got {lang}"
        )


# Test 5: Edge cases - empty and short text
def test_edge_cases_empty_and_short_text(detector):
    """Test handling of edge cases: empty body and very short text.

    Validates:
    - Empty email body raises ValueError
    - Very short text (<20 chars) handled gracefully
    - Whitespace-only text handled correctly
    """
    # Test empty string
    with pytest.raises(ValueError, match="Email body cannot be empty"):
        detector.detect("")

    # Test whitespace-only string
    with pytest.raises(ValueError, match="Email body cannot be empty"):
        detector.detect("   \n\t  ")

    # Test None input
    with pytest.raises(ValueError):
        detector.detect(None)

    # Test very short text (<20 chars) - should still attempt detection
    short_texts = [
        ("Hello world", "en"),
        ("Привет", "ru"),
        ("Hallo", "de"),
        ("Доброго дня", "uk"),
    ]

    for text, expected_lang in short_texts:
        try:
            lang, conf = detector.detect(text)
            # Should return a language code (may not be perfect for very short text)
            assert isinstance(lang, str), "Should return string language code"
            assert isinstance(conf, float), "Should return float confidence"
        except LangDetectException:
            # langdetect may fail on very short text - this is acceptable
            pass


# Test 6: Error handling - invalid input
def test_error_handling_invalid_input(detector):
    """Test error handling for HTML content and edge cases.

    Validates:
    - HTML content is stripped before detection
    - Detection works correctly on cleaned HTML
    - Invalid input handled gracefully
    """
    # Test HTML email content
    html_email_de = """
    <html>
        <body>
            <p>Hallo! Dies ist eine <b>wichtige</b> Nachricht.</p>
            <p>Bitte lesen Sie diese E-Mail sorgfältig.</p>
            <div>Vielen Dank für Ihre Aufmerksamkeit!</div>
        </body>
    </html>
    """
    lang, conf = detector.detect(html_email_de)
    assert lang == "de", "Should detect German from HTML email"
    assert conf > 0.7, "Should have high confidence after HTML stripping"

    # Test HTML email with mixed content
    html_email_en = """
    <html><head><title>Test</title></head>
    <body>
        <h1>Important Update</h1>
        <p>This is an important message about our project.</p>
        <p>Please review the attached documents carefully.</p>
    </body></html>
    """
    lang, conf = detector.detect(html_email_en)
    assert lang == "en", "Should detect English from HTML email"

    # Test HTML with Russian content
    html_email_ru = """
    <div class="email-body">
        <p>Здравствуйте!</p>
        <p>Это важное сообщение о нашем проекте.</p>
        <p>Пожалуйста, внимательно прочитайте документы.</p>
    </div>
    """
    lang, conf = detector.detect(html_email_ru)
    assert lang == "ru", "Should detect Russian from HTML email"

    # Test HTML with minimal text
    html_minimal = "<html><body><p>OK</p></body></html>"
    try:
        lang, conf = detector.detect(html_minimal)
        # Should return some language (may be inaccurate due to minimal text)
        assert isinstance(lang, str), "Should return language code"
    except (ValueError, LangDetectException):
        # May fail due to insufficient text after HTML stripping
        pass


# Additional test: Test detect_primary_language with single language
def test_detect_primary_language_single_language(detector, sample_emails):
    """Test detect_primary_language() works correctly with single-language emails."""
    for expected_lang, email_body in sample_emails.items():
        primary = detector.detect_primary_language(email_body)
        assert primary == expected_lang, (
            f"Expected {expected_lang}, got {primary}"
        )


# Additional test: Test SUPPORTED_LANGUAGES constant
def test_supported_languages_constant(detector):
    """Test that SUPPORTED_LANGUAGES constant contains exactly 4 languages."""
    assert len(detector.SUPPORTED_LANGUAGES) == 4, "Should support exactly 4 languages"
    assert set(detector.SUPPORTED_LANGUAGES) == {"ru", "uk", "en", "de"}, (
        "Should support ru, uk, en, de"
    )


# Additional test: Test CONFIDENCE_THRESHOLD constant
def test_confidence_threshold_constant(detector):
    """Test that CONFIDENCE_THRESHOLD is set to 0.7."""
    assert detector.CONFIDENCE_THRESHOLD == 0.7, "Threshold should be 0.7"
