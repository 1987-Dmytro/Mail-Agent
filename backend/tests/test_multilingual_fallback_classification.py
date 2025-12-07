"""Comprehensive tests for multilingual fallback classification.

Tests the improved fallback classification that uses:
1. LanguageDetectionService for auto-detecting email language (en/de/ru/uk)
2. ToneDetectionService (rule-based only) for tone detection (formal/professional/casual)
3. Multilingual QUESTION_INDICATORS for needs_response detection

This ensures the workflow receives ALL critical fields even when LLM fails.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.classification import EmailClassificationService, _multilingual_needs_response


class TestMultilingualNeedsResponse:
    """Test multilingual needs_response detection function."""

    @pytest.mark.parametrize("language,body,subject,expected", [
        # Russian tests
        ("ru", "Когда ты сможешь ответить?", "Вопрос", True),
        ("ru", "Что ты думаешь о плане?", "План", True),
        ("ru", "Прикрепляю документы", "Документы", False),
        ("ru", "Спасибо за информацию", "Re: Встреча", False),

        # English tests
        ("en", "When can you confirm?", "Meeting", True),
        ("en", "What do you think about this?", "Question", True),
        ("en", "Thank you for the information", "Re: Project", False),
        ("en", "Attached are the files", "Files", False),

        # German tests
        ("de", "Wann können Sie antworten?", "Anfrage", True),
        ("de", "Was denken Sie darüber?", "Frage", True),
        ("de", "Vielen Dank für die Information", "Re: Projekt", False),
        ("de", "Im Anhang finden Sie die Unterlagen", "Unterlagen", False),

        # Ukrainian tests
        ("uk", "Коли ти зможеш відповісти?", "Питання", True),
        ("uk", "Що ти думаєш про це?", "План", True),
        ("uk", "Дякую за інформацію", "Re: Зустріч", False),
        ("uk", "Додаю документи", "Документи", False),
    ])
    def test_multilingual_detection(self, language, body, subject, expected):
        """Test needs_response detection across all 4 supported languages."""
        result = _multilingual_needs_response(body, subject, language)
        assert result == expected, f"Failed for {language}: {body}"

    def test_question_mark_detection(self):
        """Test that question mark is detected across all languages."""
        for lang in ["en", "de", "ru", "uk"]:
            assert _multilingual_needs_response("Is this correct?", "Test", lang) is True

    def test_fallback_to_english(self):
        """Test that unsupported language falls back to English indicators."""
        result = _multilingual_needs_response("When can you confirm?", "Test", "fr")  # French not supported
        assert result is True  # Falls back to English indicators

    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        assert _multilingual_needs_response("WHEN can you CONFIRM?", "MEETING", "en") is True
        assert _multilingual_needs_response("когда ты сможешь?", "ВОПРОС", "ru") is True


class TestComprehensiveFallbackClassification:
    """Test comprehensive fallback classification with all fields."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_gmail_client(self):
        """Mock Gmail client."""
        return MagicMock()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        return MagicMock()

    @pytest.fixture
    def classification_service(self, mock_db, mock_gmail_client, mock_llm_client):
        """Create classification service instance."""
        return EmailClassificationService(
            db=mock_db,
            gmail_client=mock_gmail_client,
            llm_client=mock_llm_client
        )

    def test_fallback_sets_all_critical_fields_russian(self, classification_service):
        """Test that fallback sets ALL critical workflow fields for Russian email."""
        email_data = {
            "subject": "Re: Праздники",
            "body": "Когда ты сможешь точно сказать о том ждать тебя или нет?",
            "sender": "friend@gmail.com"
        }

        result = classification_service._create_fallback_classification(
            reason="Rate limit exceeded",
            email_data=email_data
        )

        # Verify ALL critical fields are set
        assert result.suggested_folder == "Important"
        assert result.detected_language == "ru"  # ← Auto-detected!
        assert result.tone == "casual"  # ← Free email provider
        assert result.needs_response is True  # ← Detected "когда"
        assert result.priority_score == 50
        assert result.confidence == 0.0
        assert result.response_draft is None
        assert "language=ru" in result.reasoning
        assert "tone=casual" in result.reasoning

    def test_fallback_sets_all_critical_fields_english(self, classification_service):
        """Test fallback for English email from business sender."""
        email_data = {
            "subject": "Project Update",
            "body": "When can you provide the status update?",
            "sender": "client@company.com"
        }

        result = classification_service._create_fallback_classification(
            reason="API timeout",
            email_data=email_data
        )

        assert result.detected_language == "en"
        assert result.tone == "professional"  # ← Business domain
        assert result.needs_response is True  # ← Detected "when"

    def test_fallback_formal_tone_government(self, classification_service):
        """Test formal tone detection for government emails."""
        email_data = {
            "subject": "Steuerbescheid 2024",
            "body": "Bitte reichen Sie Ihre Steuererklärung bis zum 31.12.2024 ein.",
            "sender": "info@finanzamt.de"
        }

        result = classification_service._create_fallback_classification(
            reason="Rate limit",
            email_data=email_data
        )

        assert result.detected_language == "de"
        assert result.tone == "formal"  # ← Government domain!
        assert result.needs_response is False  # ← No question

    def test_fallback_ukrainian_casual(self, classification_service):
        """Test Ukrainian email with casual tone."""
        email_data = {
            "subject": "Привіт!",
            "body": "Коли ти приїдеш на вечірку?",
            "sender": "friend@gmail.com"
        }

        result = classification_service._create_fallback_classification(
            reason="GeminiRateLimitError",
            email_data=email_data
        )

        assert result.detected_language == "uk"
        assert result.tone == "casual"
        assert result.needs_response is True  # ← Detected "коли"

    def test_fallback_without_email_data(self, classification_service):
        """Test fallback with no email_data uses safe defaults."""
        result = classification_service._create_fallback_classification(
            reason="Unknown error",
            email_data=None
        )

        # Should use safe defaults
        assert result.suggested_folder == "Important"
        assert result.detected_language == "en"  # ← Default
        assert result.tone == "professional"  # ← Default
        assert result.needs_response is False  # ← Default
        assert result.confidence == 0.0

    def test_fallback_language_detection_failure(self, classification_service):
        """Test fallback when language detection fails - uses safe defaults."""
        email_data = {
            "subject": "Test",
            "body": "Test body",
            "sender": "test@test.com"
        }

        # Should work with safe fallback even if language detection has issues
        result = classification_service._create_fallback_classification(
            reason="Service error",
            email_data=email_data
        )

        # Uses safe English fallback
        assert result.detected_language is not None
        # Should default to English or detected language
        assert result.detected_language in ["en", "de", "ru", "uk"]

    @pytest.mark.parametrize("sender_domain,expected_tone", [
        # Formal (government)
        ("finanzamt.de", "formal"),
        ("auslaenderbehoerde.de", "formal"),
        ("tax.gov", "formal"),
        ("irs.gov", "formal"),

        # Professional (business)
        ("company.com", "professional"),
        ("business.de", "professional"),
        ("corp.net", "professional"),

        # Casual (personal/free email)
        ("gmail.com", "casual"),
        ("yahoo.com", "casual"),
        ("hotmail.com", "casual"),
        ("outlook.com", "casual"),
        ("gmx.de", "casual"),
        ("web.de", "casual"),
    ])
    def test_tone_detection_by_domain(self, classification_service, sender_domain, expected_tone):
        """Test tone detection based on sender domain."""
        email_data = {
            "subject": "Test",
            "body": "Test email body",
            "sender": f"user@{sender_domain}"
        }

        result = classification_service._create_fallback_classification(
            reason="Test",
            email_data=email_data
        )

        assert result.tone == expected_tone, f"Failed for domain: {sender_domain}"

    def test_fallback_preserves_reasoning_with_metadata(self, classification_service):
        """Test that reasoning includes language and tone metadata."""
        email_data = {
            "subject": "Test",
            "body": "Test",
            "sender": "test@company.com"
        }

        result = classification_service._create_fallback_classification(
            reason="Custom error message",
            email_data=email_data
        )

        # Reasoning should include original reason + metadata
        assert "Custom error message" in result.reasoning
        assert "language=" in result.reasoning
        assert "tone=" in result.reasoning


class TestMultilingualWorkflowIntegration:
    """Test that all fields work correctly in workflow context."""

    def test_all_workflow_critical_fields_present(self):
        """Verify all workflow-critical fields are present in ClassificationResponse."""
        from app.models.classification_response import ClassificationResponse

        # Create instance with all fields
        response = ClassificationResponse(
            suggested_folder="Important",
            reasoning="Test reasoning for classification",
            priority_score=50,
            confidence=0.0,
            needs_response=True,
            response_draft=None,
            detected_language="ru",
            tone="casual"
        )

        # Verify all fields accessible
        assert response.suggested_folder == "Important"
        assert response.detected_language == "ru"
        assert response.tone == "casual"
        assert response.needs_response is True

        # Verify dict serialization includes all fields
        response_dict = response.to_dict()
        assert "detected_language" in response_dict
        assert "tone" in response_dict
        assert response_dict["detected_language"] == "ru"
        assert response_dict["tone"] == "casual"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
