"""Integration tests for language detection service with database.

This module tests the language detection functionality integrated with
EmailProcessingQueue database operations, validating end-to-end workflows.

Test Coverage:
- AC #3, #6: All 4 supported languages detected correctly
- AC #7: Detected language stored in database
- AC #5: Mixed-language email workflow with database storage
- AC #8: Low confidence fallback to English with database persistence
"""

from datetime import datetime, UTC

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import EmailProcessingQueue
from app.models.user import User
from app.services.language_detection import LanguageDetectionService


@pytest_asyncio.fixture
async def sample_emails_4_languages():
    """Sample email bodies for all 4 supported languages.

    Ukrainian text uses distinctive words and grammar to help differentiate from Russian.
    """
    return {
        "ru": "Здравствуйте! Это важное письмо о нашем проекте. Пожалуйста, прочитайте внимательно и подтвердите получение этого сообщения. Спасибо за внимание к данному вопросу.",
        "uk": "Вітаю! Це дуже важливий лист щодо нашого проєкту. Будь ласка, уважно ознайомтеся із усіма деталями і надайте відповідь якнайшвидше. Дякую за вашу увагу та співпрацю.",
        "en": "Hello! This is an important email about our project. Please read carefully and confirm receipt of this message. Thank you for your attention to this matter.",
        "de": "Hallo! Dies ist eine wichtige E-Mail über unser Projekt. Bitte lesen Sie sorgfältig und bestätigen Sie den Erhalt dieser Nachricht. Vielen Dank für Ihre Aufmerksamkeit.",
    }


@pytest_asyncio.fixture
def detector():
    """Initialize LanguageDetectionService for integration tests."""
    return LanguageDetectionService()


# Test 1: AC #3, #6 - Detect all 4 supported languages
@pytest.mark.asyncio
async def test_detect_all_4_supported_languages(detector, sample_emails_4_languages):
    """Test language detection for all 4 supported languages with real langdetect library.

    Validates:
    - AC #3: Supports 4 target languages (ru, uk, en, de)
    - AC #6: Language detection validated with test emails in all 4 languages
    - Real langdetect library integration (not mocked)
    - All 4 languages detected correctly with high confidence
    """
    results = {}

    for expected_lang, email_body in sample_emails_4_languages.items():
        lang_code, confidence = detector.detect(email_body)
        results[expected_lang] = {"detected": lang_code, "confidence": confidence}

        # Verify correct language detected
        assert lang_code == expected_lang, (
            f"Language detection failed for {expected_lang}: "
            f"expected {expected_lang}, got {lang_code} (confidence: {confidence:.3f})"
        )

        # Verify high confidence for clear language text
        assert confidence > 0.7, (
            f"Low confidence for {expected_lang}: {confidence:.3f} "
            f"(expected > 0.7 for clear text)"
        )

    # Summary assertion - all 4 languages should be detected
    assert len(results) == 4, "Should detect all 4 supported languages"
    assert set(results.keys()) == {"ru", "uk", "en", "de"}, (
        "Should detect exactly ru, uk, en, de"
    )


# Test 2: AC #7 - Store detected language in EmailProcessingQueue
@pytest.mark.asyncio
async def test_store_detected_language_in_email_queue(
    db_session: AsyncSession,
    test_user: User,
    detector,
    sample_emails_4_languages
):
    """Test that detected language is stored in EmailProcessingQueue.detected_language field.

    Validates:
    - AC #7: Detected language stored in EmailProcessingQueue.detected_language field
    - Language detection integrated with database workflow
    - detected_language field correctly populated for all 4 languages
    - Database persistence works correctly
    """
    for expected_lang, email_body in sample_emails_4_languages.items():
        # Detect language
        lang_code, confidence = detector.detect(email_body)

        # Create email record in EmailProcessingQueue
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=f"test_msg_{expected_lang}_123",
            gmail_thread_id=f"test_thread_{expected_lang}_123",
            sender=f"sender_{expected_lang}@example.com",
            subject=f"Test email in {expected_lang}",
            received_at=datetime.now(UTC),
            status="pending",
            detected_language=lang_code,  # Store detected language
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        # Verify detected_language field is stored correctly
        assert email.detected_language == expected_lang, (
            f"detected_language field mismatch: expected {expected_lang}, "
            f"got {email.detected_language}"
        )
        assert email.detected_language is not None, (
            "detected_language field should not be None"
        )

        # Verify can retrieve from database
        from sqlalchemy import select
        result = await db_session.execute(
            select(EmailProcessingQueue).where(
                EmailProcessingQueue.gmail_message_id == f"test_msg_{expected_lang}_123"
            )
        )
        retrieved_email = result.scalar_one()
        assert retrieved_email.detected_language == expected_lang, (
            f"Retrieved email detected_language mismatch: "
            f"expected {expected_lang}, got {retrieved_email.detected_language}"
        )


# Test 3: AC #5 - Mixed-language email workflow with database storage
@pytest.mark.asyncio
async def test_mixed_language_email_workflow(
    db_session: AsyncSession,
    test_user: User,
    detector
):
    """Test mixed-language email detection with database integration.

    Validates:
    - AC #5: Mixed-language emails handled using primary detected language
    - Primary language (highest probability) is stored in database
    - Works correctly for various language combinations
    """
    # Mixed German (70%) + English (30%) email
    mixed_email_de_en = """
    Hallo! Dies ist eine sehr wichtige Nachricht über unser Projekt.
    Die Details sind äußerst wichtig für das gesamte Team.
    Bitte lesen Sie sorgfältig und antworten Sie bis morgen.
    We need to discuss this in the next meeting.
    Thank you for your attention to this matter.
    """

    # Detect primary language
    primary_lang = detector.detect_primary_language(mixed_email_de_en)
    assert primary_lang == "de", (
        f"Primary language should be German for mostly German text, got {primary_lang}"
    )

    # Store in database
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="test_msg_mixed_de_en_456",
        gmail_thread_id="test_thread_mixed_456",
        sender="sender_mixed@example.com",
        subject="Mixed German/English email",
        received_at=datetime.now(UTC),
        status="pending",
        detected_language=primary_lang,
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Verify primary language stored in database
    assert email.detected_language == "de", (
        f"Database should store primary language 'de', got {email.detected_language}"
    )

    # Test another mixed-language combination: Russian (60%) + English (40%)
    mixed_email_ru_en = """
    Здравствуйте! Это очень важное сообщение о нашем проекте.
    Пожалуйста, внимательно прочитайте все детали.
    Нужно обсудить это на следующей встрече.
    Please confirm receipt of this email.
    Thank you for your cooperation.
    """

    primary_lang_ru = detector.detect_primary_language(mixed_email_ru_en)
    assert primary_lang_ru == "ru", (
        f"Primary language should be Russian for mostly Russian text, got {primary_lang_ru}"
    )

    # Store second mixed email
    email_ru = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="test_msg_mixed_ru_en_789",
        gmail_thread_id="test_thread_mixed_789",
        sender="sender_mixed_ru@example.com",
        subject="Mixed Russian/English email",
        received_at=datetime.now(UTC),
        status="pending",
        detected_language=primary_lang_ru,
    )
    db_session.add(email_ru)
    await db_session.commit()
    await db_session.refresh(email_ru)

    assert email_ru.detected_language == "ru", (
        f"Database should store primary language 'ru', got {email_ru.detected_language}"
    )


# Test 4: AC #8 - Low confidence fallback to English with database persistence
@pytest.mark.asyncio
async def test_low_confidence_fallback_to_english(
    db_session: AsyncSession,
    test_user: User,
    detector
):
    """Test fallback to English when confidence is low (<0.7) with database storage.

    Validates:
    - AC #8: Fallback to English implemented when detection confidence is low (<0.7)
    - Fallback language ("en") is stored in database
    - Confidence threshold (0.7) applied correctly
    - Works with various ambiguous inputs
    """
    # Very short ambiguous text (likely low confidence)
    ambiguous_text = "OK thx see u"

    # Detect with fallback
    lang, confidence = detector.detect_with_fallback(ambiguous_text)

    # If confidence < 0.7, should fallback to English
    if confidence < 0.7:
        assert lang == "en", (
            f"Should fallback to 'en' for low confidence {confidence:.3f}, got {lang}"
        )

    # Store in database
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="test_msg_low_conf_001",
        gmail_thread_id="test_thread_low_conf_001",
        sender="sender_ambiguous@example.com",
        subject="Ambiguous short text",
        received_at=datetime.now(UTC),
        status="pending",
        detected_language=lang,
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Verify fallback language stored in database
    if confidence < 0.7:
        assert email.detected_language == "en", (
            f"Database should store fallback language 'en', got {email.detected_language}"
        )

    # Test another ambiguous case with numbers and symbols
    ambiguous_numbers = "123 OK @test #project"
    lang2, conf2 = detector.detect_with_fallback(ambiguous_numbers)

    email2 = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="test_msg_low_conf_002",
        gmail_thread_id="test_thread_low_conf_002",
        sender="sender_numbers@example.com",
        subject="Numbers and symbols",
        received_at=datetime.now(UTC),
        status="pending",
        detected_language=lang2,
    )
    db_session.add(email2)
    await db_session.commit()
    await db_session.refresh(email2)

    # Should store a valid language code
    assert email2.detected_language in ["ru", "uk", "en", "de"], (
        f"Should store a valid language code, got {email2.detected_language}"
    )

    # Test custom fallback language
    custom_fallback = "de"
    lang3, conf3 = detector.detect_with_fallback("123", fallback_lang=custom_fallback)

    if conf3 < 0.7:
        assert lang3 == custom_fallback, (
            f"Should use custom fallback '{custom_fallback}', got {lang3}"
        )
