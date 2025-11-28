"""Unit tests for response generation prompt engineering.

This test module covers:
- Tone detection (government domains, business clients, personal contacts)
- Prompt template formatting with all placeholders
- Greeting/closing selection for language+tone combinations
- Prompt length constraints and formality instructions
- Multilingual support (de, en, ru, uk)
- Prompt version storage and retrieval

Test Count: 8 unit test functions as specified in Story 3.6 acceptance criteria.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.services.tone_detection import ToneDetectionService, GOVERNMENT_DOMAINS
from app.prompts.response_generation import (
    format_response_prompt,
    GREETING_EXAMPLES,
    CLOSING_EXAMPLES,
    LANGUAGE_NAMES,
    _format_thread_history,
    _format_semantic_results,
)
from app.config.prompts_config import save_prompt_version, load_prompt_version
from app.models.email import EmailProcessingQueue
from app.models.prompt_versions import PromptVersion


# Fixtures for test data

@pytest.fixture
def mock_email_government():
    """Mock email from German government domain."""
    email = Mock(spec=EmailProcessingQueue)
    email.sender = "info@finanzamt.de"
    email.subject = "Steuererklärung 2024"
    email.body = "Sehr geehrte Damen und Herren, bitte reichen Sie Ihre Steuererklärung ein."
    return email


@pytest.fixture
def mock_email_business():
    """Mock email from business client."""
    email = Mock(spec=EmailProcessingQueue)
    email.sender = "contact@business-company.com"
    email.subject = "Project Update"
    email.body = "Hello, I wanted to update you on the project status."
    return email


@pytest.fixture
def mock_email_personal():
    """Mock email from personal contact."""
    email = Mock(spec=EmailProcessingQueue)
    email.sender = "friend@gmail.com"
    email.subject = "Coffee this week?"
    email.body = "Hey! Want to grab coffee sometime this week?"
    return email


@pytest.fixture
def mock_rag_context():
    """Mock RAG context with thread history and semantic results."""
    return {
        "thread_history": [
            {
                "sender": "user@example.com",
                "sent_at": datetime(2024, 1, 1, 10, 0),
                "body": "Initial inquiry about the project timeline.",
            },
            {
                "sender": "team@example.com",
                "sent_at": datetime(2024, 1, 2, 14, 30),
                "body": "Response with preliminary timeline estimates.",
            },
        ],
        "semantic_results": [
            {
                "sender": "similar@example.com",
                "sent_at": datetime(2023, 12, 15),
                "body": "Similar project discussion from previous client.",
                "similarity_score": 0.92,
            },
            {
                "sender": "related@example.com",
                "sent_at": datetime(2023, 11, 20),
                "body": "Related technical details about implementation.",
                "similarity_score": 0.85,
            },
        ],
    }


# Test 1: AC #4 - Tone detection for government domains
def test_tone_detection_government_domains(mock_email_government):
    """Test that emails from government domains return 'formal' tone.

    AC #4: Tone detection logic implemented (formal for government)
    """
    service = ToneDetectionService()

    # Test multiple government domains
    government_emails = [
        "info@finanzamt.de",
        "contact@auslaenderbehoerde.de",
        "service@bundesagentur-fuer-arbeit.de",
        "admin@stadt.de",
    ]

    for sender in government_emails:
        mock_email_government.sender = sender
        tone = service.detect_tone(mock_email_government, thread_history=[])

        assert tone == "formal", f"Expected 'formal' tone for {sender}, got {tone}"


# Test 2: AC #4 - Tone detection for business clients
def test_tone_detection_business_clients(mock_email_business):
    """Test that known business client emails return 'professional' tone.

    AC #4: Tone detection logic implemented (professional for business)
    """
    service = ToneDetectionService()

    # Business domains (not free email providers, not government)
    business_emails = [
        "contact@business-company.com",
        "sales@tech-startup.io",
        "info@consulting-firm.co.uk",
    ]

    for sender in business_emails:
        mock_email_business.sender = sender
        tone = service.detect_tone(mock_email_business, thread_history=[])

        assert tone == "professional", f"Expected 'professional' tone for {sender}, got {tone}"


# Test 3: AC #4 - Tone detection for personal contacts
def test_tone_detection_personal_contacts(mock_email_personal):
    """Test that personal contact emails return 'casual' tone.

    AC #4: Tone detection logic implemented (casual for personal)
    """
    service = ToneDetectionService()

    # Personal emails (free email providers)
    personal_emails = [
        "friend@gmail.com",
        "buddy@yahoo.com",
        "colleague@hotmail.com",
        "family@outlook.com",
    ]

    for sender in personal_emails:
        mock_email_personal.sender = sender
        tone = service.detect_tone(mock_email_personal, thread_history=[])

        assert tone == "casual", f"Expected 'casual' tone for {sender}, got {tone}"


# Test 4: AC #1, #2 - Prompt template formatting with all placeholders
def test_prompt_template_formatting(mock_email_business, mock_rag_context):
    """Test that format_response_prompt substitutes all placeholders correctly.

    AC #1: Response prompt template created with placeholders
    AC #2: Prompt includes original email, thread summary, RAG context
    """
    email = mock_email_business
    email.sender = "client@business.com"
    email.subject = "Project Discussion"
    email.body = "Let's discuss the project timeline and deliverables."

    prompt = format_response_prompt(
        email=email,
        rag_context=mock_rag_context,
        language="en",
        tone="professional",
    )

    # Verify all major sections present
    assert "ORIGINAL EMAIL" in prompt
    assert "From: client@business.com" in prompt
    assert "Subject: Project Discussion" in prompt
    assert "Language: English" in prompt

    assert "CONVERSATION CONTEXT" in prompt
    assert "Thread History" in prompt
    assert "Semantic Search" in prompt

    assert "RESPONSE REQUIREMENTS" in prompt
    assert "Language: Write the response in English" in prompt
    assert "Tone: Professional" in prompt
    assert "2-3 paragraphs maximum" in prompt

    assert "GREETING AND CLOSING EXAMPLES" in prompt
    assert "Hello" in prompt  # Professional English greeting
    assert "Best regards" in prompt  # Professional English closing


# Test 5: AC #1 - Greeting/closing selection for language+tone combinations
def test_greeting_closing_selection():
    """Test appropriate greetings/closings selected for language+tone combinations.

    AC #1: Greeting/closing examples for all language+tone combinations
    """
    # Test all 12 combinations (4 languages × 3 tones)
    test_cases = [
        ("de", "formal", "Sehr geehrte Damen und Herren", "Mit freundlichen Grüßen"),
        ("de", "professional", "Guten Tag", "Beste Grüße"),
        ("de", "casual", "Hallo", "Viele Grüße"),
        ("en", "formal", "Dear Sir or Madam", "Yours faithfully"),
        ("en", "professional", "Hello", "Best regards"),
        ("en", "casual", "Hi", "Cheers"),
        ("ru", "formal", "Уважаемые дамы и господа", "С уважением"),
        ("ru", "professional", "Здравствуйте", "С наилучшими пожеланиями"),
        ("ru", "casual", "Привет", "Всего хорошего"),
        ("uk", "formal", "Шановні пані та панове", "З повагою"),
        ("uk", "professional", "Вітаю", "З найкращими побажаннями"),
        ("uk", "casual", "Привіт", "Усього найкращого"),
    ]

    for language, tone, expected_greeting_part, expected_closing in test_cases:
        # Get greeting and closing from dictionaries
        greeting_template = GREETING_EXAMPLES[language][tone]
        closing = CLOSING_EXAMPLES[language][tone]

        # Verify greeting contains expected text (before {name} placeholder)
        assert expected_greeting_part in greeting_template, (
            f"Expected greeting '{expected_greeting_part}' not found in {language}+{tone}"
        )

        # Verify closing matches exactly
        assert closing == expected_closing, (
            f"Expected closing '{expected_closing}', got '{closing}' for {language}+{tone}"
        )


# Test 6: AC #7 - Prompt includes length constraints
def test_prompt_length_constraints(mock_email_business, mock_rag_context):
    """Test that prompt includes length constraint instructions.

    AC #7: Prompt includes constraints (length, formality level)
    """
    prompt = format_response_prompt(
        email=mock_email_business,
        rag_context=mock_rag_context,
        language="en",
        tone="professional",
    )

    # Verify length constraints present
    assert "2-3 paragraphs maximum" in prompt

    # Test formality instructions for all three tones
    formal_prompt = format_response_prompt(
        email=mock_email_business,
        rag_context=mock_rag_context,
        language="de",
        tone="formal",
    )
    assert "formal language" in formal_prompt.lower()
    assert "avoid contractions" in formal_prompt.lower()

    professional_prompt = format_response_prompt(
        email=mock_email_business,
        rag_context=mock_rag_context,
        language="en",
        tone="professional",
    )
    assert "professional" in professional_prompt.lower()

    casual_prompt = format_response_prompt(
        email=mock_email_business,
        rag_context=mock_rag_context,
        language="en",
        tone="casual",
    )
    assert "friendly" in casual_prompt.lower() or "conversational" in casual_prompt.lower()


# Test 7: AC #3 - Multilingual support for all 4 languages
def test_prompt_multilingual_support(mock_email_business, mock_rag_context):
    """Test prompt generation works for all 4 supported languages.

    AC #3: Prompt instructs LLM to generate response in specified language
    """
    languages = ["de", "en", "ru", "uk"]
    expected_language_names = {
        "de": "German",
        "en": "English",
        "ru": "Russian",
        "uk": "Ukrainian",
    }

    for lang_code in languages:
        prompt = format_response_prompt(
            email=mock_email_business,
            rag_context=mock_rag_context,
            language=lang_code,
            tone="professional",
        )

        # Verify language name mapping correct
        expected_name = expected_language_names[lang_code]
        assert expected_name in prompt, f"Language name '{expected_name}' not found in prompt for {lang_code}"

        # Verify language code present
        assert f"({lang_code})" in prompt, f"Language code '({lang_code})' not found in prompt"

        # Verify language-specific greeting/closing present
        greeting = GREETING_EXAMPLES[lang_code]["professional"]
        closing = CLOSING_EXAMPLES[lang_code]["professional"]
        # Check for base greeting text (without {name} substitution)
        assert any(part in prompt for part in greeting.split("{name}")), (
            f"Greeting not found for {lang_code}"
        )
        assert closing in prompt, f"Closing '{closing}' not found for {lang_code}"


# Test 8: AC #8 - Prompt version storage and retrieval
def test_prompt_version_storage():
    """Test that prompt versions are saved and loaded correctly.

    AC #8: Prompt version stored in config for refinement
    """
    from sqlmodel import Session, select
    from app.api.deps import engine
    import uuid

    # Use unique template name for test isolation
    template_name = f"test_response_generation_{uuid.uuid4().hex[:8]}"
    template_content = "Test prompt template with {placeholders}"
    version = "1.0.0"
    parameters = {"token_budget": 6500, "max_paragraphs": 3}

    try:
        # Test save_prompt_version creates a new version
        saved_version = save_prompt_version(
            template_name=template_name,
            template_content=template_content,
            version=version,
            parameters=parameters,
        )

        assert saved_version is not None
        assert saved_version.template_name == template_name
        assert saved_version.version == version
        assert saved_version.is_active == True
        assert saved_version.template_content == template_content
        assert saved_version.parameters == parameters

        # Test load_prompt_version retrieves the version
        loaded_version = load_prompt_version(template_name)

        assert loaded_version is not None
        assert loaded_version.template_name == template_name
        assert loaded_version.version == version
        assert loaded_version.is_active == True

        # Test loading specific version
        loaded_specific = load_prompt_version(template_name, version="1.0.0")
        assert loaded_specific is not None
        assert loaded_specific.version == "1.0.0"

    finally:
        # Cleanup: Delete test prompt versions
        with Session(engine) as session:
            test_versions = session.exec(
                select(PromptVersion).where(PromptVersion.template_name == template_name)
            ).all()
            for pv in test_versions:
                session.delete(pv)
            session.commit()
