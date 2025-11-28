"""Integration tests for response generation prompt engineering.

This test module covers end-to-end prompt generation scenarios:
- Formal German government email prompts
- Professional English business email prompts
- Casual Russian personal email prompts
- Multilingual prompt quality across all 4 languages
- Real Gemini API tone detection for ambiguous cases

Test Count: 5 integration test functions as specified in Story 3.6.

Requirements:
- Real LanguageDetectionService from Story 3.5
- Test database for Email and RAGContext integration
- Real Gemini API for LLM-based tone detection test (marked as slow)
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.models.email import EmailProcessingQueue
from app.models.user import User
from app.services.tone_detection import ToneDetectionService
from app.services.language_detection import LanguageDetectionService
from app.prompts.response_generation import format_response_prompt, GREETING_EXAMPLES, CLOSING_EXAMPLES
from app.api.deps import engine


# Fixtures for integration test data

@pytest.fixture
def test_user():
    """Create a test user for email associations."""
    with Session(engine) as session:
        user = User(
            email="test@example.com",
            name="Test User",
            is_active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        yield user

        # Cleanup
        session.delete(user)
        session.commit()


@pytest.fixture
def sample_german_government_email(test_user):
    """Sample email from German government (Finanzamt)."""
    # Create email object for testing (body field added dynamically, not stored in DB)
    from unittest.mock import Mock
    email = Mock(spec=EmailProcessingQueue)
    email.id = 1
    email.user_id = test_user.id
    email.gmail_message_id = f"gov_test_{datetime.now(timezone.utc).timestamp()}"
    email.gmail_thread_id = "thread_gov_001"
    email.sender = "info@finanzamt.de"
    email.subject = "Steuererklärung 2024 - Frist"
    email.received_at = datetime.now(timezone.utc)
    email.status = "pending"
    email.body = "Sehr geehrte Damen und Herren,\n\nwir erinnern Sie an die Abgabefrist Ihrer Steuererklärung für das Jahr 2024. Bitte reichen Sie alle erforderlichen Unterlagen bis zum 31. Juli ein."

    yield email


@pytest.fixture
def sample_english_business_email(test_user):
    """Sample email from English business client."""
    from unittest.mock import Mock
    email = Mock(spec=EmailProcessingQueue)
    email.id = 2
    email.user_id = test_user.id
    email.gmail_message_id = f"biz_test_{datetime.now(timezone.utc).timestamp()}"
    email.gmail_thread_id = "thread_biz_001"
    email.sender = "contact@tech-startup.io"
    email.subject = "Q4 Project Timeline Discussion"
    email.received_at = datetime.now(timezone.utc)
    email.status = "pending"
    email.body = "Hello,\n\nI hope this email finds you well. I wanted to discuss the timeline for our Q4 project deliverables. Can we schedule a meeting next week to align on milestones?"

    yield email


@pytest.fixture
def sample_russian_personal_email(test_user):
    """Sample email from Russian personal contact."""
    from unittest.mock import Mock
    email = Mock(spec=EmailProcessingQueue)
    email.id = 3
    email.user_id = test_user.id
    email.gmail_message_id = f"personal_test_{datetime.now(timezone.utc).timestamp()}"
    email.gmail_thread_id = "thread_personal_001"
    email.sender = "friend@mail.ru"
    email.subject = "Встреча на выходных"
    email.received_at = datetime.now(timezone.utc)
    email.status = "pending"
    email.body = "Привет!\n\nКак дела? Может встретимся на выходных? Хочу обсудить наши планы на отпуск."

    yield email


@pytest.fixture
def sample_rag_context():
    """Mock RAG context for testing."""
    return {
        "thread_history": [
            {
                "sender": "previous@example.com",
                "sent_at": datetime(2024, 1, 1, 10, 0),
                "body": "Initial message in the conversation thread.",
            },
        ],
        "semantic_results": [
            {
                "sender": "similar@example.com",
                "sent_at": datetime(2023, 12, 15),
                "body": "Similar topic discussed in previous email.",
                "similarity_score": 0.87,
            },
        ],
    }


# Integration Test 1: AC #4, #5, #6 - Formal German government email
def test_formal_german_government_email_prompt(
    sample_german_government_email, sample_rag_context
):
    """Test complete prompt generation for formal German government email.

    AC #4: Tone detection (formal for government)
    AC #5: Prompt examples created showing expected output
    AC #6: Testing performed with sample emails

    Verifies:
    - Tone detection returns "formal" for Finanzamt email
    - Language detection returns "de" (German)
    - Prompt includes formal German greeting ("Sehr geehrte")
    - Prompt includes formal German closing ("Mit freundlichen Grüßen")
    - Prompt contains formal tone instructions
    """
    email = sample_german_government_email

    # Detect tone using ToneDetectionService
    tone_service = ToneDetectionService()
    detected_tone = tone_service.detect_tone(email, thread_history=[])

    assert detected_tone == "formal", f"Expected 'formal' tone for Finanzamt email, got {detected_tone}"

    # Detect language using LanguageDetectionService from Story 3.5
    lang_service = LanguageDetectionService()
    detected_language, confidence = lang_service.detect(email.body)

    assert detected_language == "de", f"Expected 'de' language, got {detected_language}"
    assert confidence > 0.8, f"Expected high confidence, got {confidence}"

    # Generate complete prompt
    prompt = format_response_prompt(
        email=email,
        rag_context=sample_rag_context,
        language=detected_language,
        tone=detected_tone,
    )

    # Verify formal German greeting and closing present
    formal_de_greeting = GREETING_EXAMPLES["de"]["formal"]
    formal_de_closing = CLOSING_EXAMPLES["de"]["formal"]

    assert formal_de_greeting in prompt, f"Formal German greeting not found: {formal_de_greeting}"
    assert formal_de_closing in prompt, f"Formal German closing not found: {formal_de_closing}"

    # Verify tone instructions
    assert "formal" in prompt.lower()
    assert "German" in prompt

    # Verify original email content present
    assert "info@finanzamt.de" in prompt
    assert "Steuererklärung" in prompt


# Integration Test 2: AC #4, #5, #6 - Professional English business email
def test_professional_english_business_email_prompt(
    sample_english_business_email, sample_rag_context
):
    """Test prompt generation for professional English business email.

    AC #4: Tone detection (professional for business)
    AC #5: Prompt examples created showing expected output
    AC #6: Testing performed with sample emails

    Verifies:
    - Tone detection returns "professional"
    - Language detection returns "en" (English)
    - Prompt includes professional English greeting ("Hello")
    - Prompt includes professional English closing ("Best regards")
    - RAG context integration works correctly
    """
    email = sample_english_business_email

    # Detect tone
    tone_service = ToneDetectionService()
    detected_tone = tone_service.detect_tone(email, thread_history=[])

    assert detected_tone == "professional", f"Expected 'professional' tone, got {detected_tone}"

    # Detect language
    lang_service = LanguageDetectionService()
    detected_language, confidence = lang_service.detect(email.body)

    assert detected_language == "en", f"Expected 'en' language, got {detected_language}"

    # Generate prompt
    prompt = format_response_prompt(
        email=email,
        rag_context=sample_rag_context,
        language=detected_language,
        tone=detected_tone,
    )

    # Verify professional English greeting/closing
    prof_en_greeting_part = "Hello"  # Part of "Hello {name}"
    prof_en_closing = CLOSING_EXAMPLES["en"]["professional"]

    assert prof_en_greeting_part in prompt
    assert prof_en_closing in prompt

    # Verify tone and language
    assert "professional" in prompt.lower()
    assert "English" in prompt

    # Verify RAG context integration
    assert "CONVERSATION CONTEXT" in prompt
    assert "Thread History" in prompt
    assert "Semantic" in prompt or "Relevance" in prompt


# Integration Test 3: AC #4, #5, #6 - Casual Russian personal email
def test_casual_russian_personal_email_prompt(
    sample_russian_personal_email, sample_rag_context
):
    """Test prompt generation for casual Russian personal email.

    AC #4: Tone detection (casual for personal)
    AC #5: Prompt examples created showing expected output
    AC #6: Testing performed with sample emails

    Verifies:
    - Tone detection returns "casual"
    - Language detection returns "ru" (Russian)
    - Prompt includes casual Russian greeting ("Привет")
    - Prompt includes casual Russian closing ("Всего хорошего")
    """
    email = sample_russian_personal_email

    # Detect tone
    tone_service = ToneDetectionService()
    detected_tone = tone_service.detect_tone(email, thread_history=[])

    assert detected_tone == "casual", f"Expected 'casual' tone for personal email, got {detected_tone}"

    # Detect language
    lang_service = LanguageDetectionService()
    detected_language, confidence = lang_service.detect(email.body)

    assert detected_language == "ru", f"Expected 'ru' language, got {detected_language}"

    # Generate prompt
    prompt = format_response_prompt(
        email=email,
        rag_context=sample_rag_context,
        language=detected_language,
        tone=detected_tone,
    )

    # Verify casual Russian greeting/closing
    casual_ru_greeting_part = "Привет"
    casual_ru_closing = CLOSING_EXAMPLES["ru"]["casual"]

    assert casual_ru_greeting_part in prompt
    assert casual_ru_closing in prompt

    # Verify tone
    assert "casual" in prompt.lower() or "friendly" in prompt.lower()
    assert "Russian" in prompt


# Integration Test 4: AC #3, #5, #6 - Multilingual prompt quality
def test_multilingual_prompt_quality(test_user, sample_rag_context):
    """Test prompt generation for emails in all 4 supported languages.

    AC #3: Prompt instructs LLM to generate response in specified language
    AC #5: Prompt examples created showing expected output
    AC #6: Testing performed with sample emails across languages

    Verifies language-specific greetings/closings correct for de, en, ru, uk.
    """
    languages_test_data = [
        ("de", "Hallo, wie geht es dir? Ich hoffe, dass es dir gut geht und du einen schönen Tag hast.", "professional", "Guten Tag", "Beste Grüße"),
        ("en", "Hello, how are you doing? I hope this message finds you well and you're having a great day.", "professional", "Hello", "Best regards"),
        ("ru", "Привет, как дела? Я надеюсь, что у тебя всё хорошо и ты отлично проводишь время.", "professional", "Здравствуйте", "С наилучшими пожеланиями"),
        ("uk", "Привіт, як справи? Я сподіваюся, що у тебе все добре і ти чудово проводиш час.", "professional", "Вітаю", "З найкращими побажаннями"),
    ]

    lang_service = LanguageDetectionService()

    for expected_lang, body_text, tone, expected_greeting_part, expected_closing in languages_test_data:
        from unittest.mock import Mock
        # Create test email (mock with body field)
        email = Mock(spec=EmailProcessingQueue)
        email.id = 100
        email.user_id = test_user.id
        email.gmail_message_id = f"multilang_{expected_lang}_{datetime.now(timezone.utc).timestamp()}"
        email.gmail_thread_id = f"thread_{expected_lang}"
        email.sender = f"test@example.{expected_lang}"
        email.subject = "Test Subject"
        email.received_at = datetime.now(timezone.utc)
        email.status = "pending"
        email.body = body_text

        # Detect language
        detected_lang, confidence = lang_service.detect(email.body)

        # Allow some flexibility for ru/uk detection (they're similar)
        if expected_lang in ["ru", "uk"]:
            assert detected_lang in ["ru", "uk"], f"Expected ru/uk, got {detected_lang} for '{body_text}'"
        else:
            assert detected_lang == expected_lang, f"Expected {expected_lang}, got {detected_lang}"

        # Generate prompt
        prompt = format_response_prompt(
            email=email,
            rag_context=sample_rag_context,
            language=expected_lang,  # Use expected language for testing
            tone=tone,
        )

        # Verify language-specific greeting and closing
        assert expected_greeting_part in prompt, (
            f"Expected greeting '{expected_greeting_part}' not found for {expected_lang}"
        )
        assert expected_closing in prompt, (
            f"Expected closing '{expected_closing}' not found for {expected_lang}"
        )


# Integration Test 5: AC #4 - LLM-based tone detection with real Gemini
@pytest.mark.slow
def test_tone_detection_with_real_gemini(test_user):
    """Test LLM-based tone detection for ambiguous email using real Gemini API.

    AC #4: Tone detection logic implemented

    This test uses the real Gemini API to verify LLM-based tone detection
    for ambiguous cases where rule-based detection is insufficient.

    Marked as @pytest.mark.slow due to API call latency.
    """
    # Create ambiguous email (neither clear government, business, nor personal)
    from unittest.mock import Mock
    ambiguous_email = Mock(spec=EmailProcessingQueue)
    ambiguous_email.id = 200
    ambiguous_email.user_id = test_user.id
    ambiguous_email.gmail_message_id = f"ambiguous_test_{datetime.now(timezone.utc).timestamp()}"
    ambiguous_email.gmail_thread_id = "thread_ambiguous"
    ambiguous_email.sender = "unknown@ambiguous-domain.com"
    ambiguous_email.subject = "Important Matter"
    ambiguous_email.received_at = datetime.now(timezone.utc)
    ambiguous_email.status = "pending"
    # Formal-sounding email but from unknown domain
    ambiguous_email.body = """Dear Colleague,

I am writing to you regarding the matter we discussed at the conference last month.
Could you please provide your expert opinion on the proposed methodology?

Thank you for your consideration."""

    # Detect tone (should fallback to LLM)
    tone_service = ToneDetectionService()
    detected_tone = tone_service.detect_tone(ambiguous_email, thread_history=[])

    # Verify tone is one of the valid options
    assert detected_tone in ["formal", "professional", "casual"], (
        f"Invalid tone returned: {detected_tone}"
    )

    # For this specific email, expect formal or professional (not casual)
    assert detected_tone in ["formal", "professional"], (
        f"Expected formal/professional tone for formal-sounding email, got {detected_tone}"
    )
