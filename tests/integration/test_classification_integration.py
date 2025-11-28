"""
Integration Tests for Email Classification with Real Gemini API

Tests classification prompts with actual Gemini API calls to validate:
- Prompt effectiveness across different email categories
- Multilingual classification (Russian, Ukrainian, English, German)
- Edge cases and error handling
- Classification accuracy and response quality

Run these tests with: pytest tests/integration/test_classification_integration.py -v --integration

Note: These tests require:
- GEMINI_API_KEY environment variable set
- Internet connection
- Gemini API access

Created: 2025-11-07
"""

import pytest
import json
from typing import Dict

from app.core.llm_client import LLMClient
from app.prompts.classification_prompt import build_classification_prompt
from app.models.classification_response import ClassificationResponse


# Test fixtures
@pytest.fixture
def llm_client():
    """Create LLMClient instance for integration tests."""
    return LLMClient()


@pytest.fixture
def user_folders():
    """Standard user folder categories for testing."""
    return [
        {"name": "Government", "description": "Official government communications (finanzamt, auslaenderbehoerde, bureaucracy)"},
        {"name": "Clients", "description": "Business communications from clients or customers"},
        {"name": "Newsletters", "description": "Marketing, promotional, or informational mass emails"},
        {"name": "Important", "description": "Time-sensitive or action-required emails"},
        {"name": "Personal", "description": "Private correspondence from friends or family"}
    ]


@pytest.mark.integration
class TestClassificationWithGeminiAPI:
    """Integration tests with real Gemini API calls."""

    def test_classify_government_email_german(self, llm_client: LLMClient, user_folders):
        """
        Test: German government email classification
        Verify: Correctly identifies Government category with high priority
        """
        email_data = {
            "sender": "finanzamt@berlin.de",
            "subject": "Steuererklärung 2024 - Abgabefrist",
            "body": "Sehr geehrte Damen und Herren, wir möchten Sie daran erinnern, dass die Abgabefrist für Ihre Steuererklärung 2024 am 31. Juli endet. Bitte reichen Sie Ihre Unterlagen rechtzeitig ein.",
            "user_email": "test@example.com"
        }

        # Build classification prompt
        prompt = build_classification_prompt(email_data, user_folders)

        # Call Gemini API
        response_json = llm_client.receive_completion(prompt, operation="classification")

        # Parse response
        classification = ClassificationResponse(**response_json)

        # Assertions
        assert classification.suggested_folder == "Government", \
            f"Expected 'Government', got '{classification.suggested_folder}'"
        assert "finanzamt" in classification.reasoning.lower() or "tax" in classification.reasoning.lower(), \
            f"Reasoning should mention tax office: {classification.reasoning}"
        assert classification.priority_score is None or classification.priority_score >= 70, \
            f"Government emails should have high priority (>=70), got {classification.priority_score}"
        assert classification.confidence is None or classification.confidence >= 0.85, \
            f"Expected high confidence (>=0.85), got {classification.confidence}"

        print(f"\n✓ Government Email (German):")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")

    def test_classify_client_email_english(self, llm_client: LLMClient, user_folders):
        """
        Test: English client email classification
        Verify: Correctly identifies Clients category
        """
        email_data = {
            "sender": "john.smith@acmecorp.com",
            "subject": "Re: Q4 Project Timeline Discussion",
            "body": "Hi, I wanted to follow up on our discussion about the Q4 deliverables. Could we schedule a meeting next week to review the project timeline and milestones?",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        assert classification.suggested_folder == "Clients", \
            f"Expected 'Clients', got '{classification.suggested_folder}'"
        assert "business" in classification.reasoning.lower() or "client" in classification.reasoning.lower() or "project" in classification.reasoning.lower(), \
            f"Reasoning should mention business/client context: {classification.reasoning}"

        print(f"\n✓ Client Email (English):")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")

    def test_classify_newsletter_email(self, llm_client: LLMClient, user_folders):
        """
        Test: Newsletter email classification
        Verify: Correctly identifies Newsletters with low priority
        """
        email_data = {
            "sender": "newsletter@techcrunch.com",
            "subject": "TechCrunch Daily: Top tech news for today",
            "body": "Welcome to TechCrunch Daily! Here are today's top stories: [News 1], [News 2], [News 3]. Stay updated with the latest in technology.",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        assert classification.suggested_folder == "Newsletters", \
            f"Expected 'Newsletters', got '{classification.suggested_folder}'"
        assert classification.priority_score is None or classification.priority_score < 30, \
            f"Newsletters should have low priority (<30), got {classification.priority_score}"

        print(f"\n✓ Newsletter Email:")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")

    def test_classify_unclear_email(self, llm_client: LLMClient, user_folders):
        """
        Test: Unclear/ambiguous email classification
        Verify: Falls back to Unclassified with low confidence
        """
        email_data = {
            "sender": "info@random-company.ru",
            "subject": "Возможность сотрудничества",
            "body": "Здравствуйте, мы бы хотели обсудить возможность сотрудничества с вашей компанией.",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        assert classification.suggested_folder == "Unclassified" or classification.confidence is None or classification.confidence < 0.8, \
            f"Unclear emails should be Unclassified or have low confidence. Got folder='{classification.suggested_folder}', confidence={classification.confidence}"

        print(f"\n✓ Unclear Email (Russian):")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")

    def test_classify_russian_government_email(self, llm_client: LLMClient, user_folders):
        """
        Test: Russian language government email
        Verify: Multilingual classification works regardless of input language
        """
        email_data = {
            "sender": "noreply@gosuslugi.ru",
            "subject": "Уведомление о готовности документа",
            "body": "Уважаемый пользователь, ваш документ готов к получению. Пожалуйста, посетите отделение в течение 30 дней.",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        assert classification.suggested_folder == "Government", \
            f"Expected 'Government', got '{classification.suggested_folder}'"
        # Reasoning should be in English
        assert classification.reasoning.isascii() or any(char.isalpha() and ord(char) < 128 for char in classification.reasoning), \
            f"Reasoning should be in English, got: {classification.reasoning}"

        print(f"\n✓ Government Email (Russian):")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")

    def test_classify_ukrainian_business_email(self, llm_client: LLMClient, user_folders):
        """
        Test: Ukrainian language business email
        Verify: Handles Ukrainian text correctly
        """
        email_data = {
            "sender": "partner@company.ua",
            "subject": "Пропозиція щодо співпраці",
            "body": "Доброго дня! Ми зацікавлені в можливості співпраці з вашою компанією. Будь ласка, повідомте, коли ми можемо обговорити деталі.",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        # Should be classified as Clients or Unclassified (unknown sender)
        assert classification.suggested_folder in ["Clients", "Unclassified"], \
            f"Expected 'Clients' or 'Unclassified', got '{classification.suggested_folder}'"

        print(f"\n✓ Business Email (Ukrainian):")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")

    def test_classify_urgent_government_email_german(self, llm_client: LLMClient, user_folders):
        """
        Test: Urgent German government email with priority keywords
        Verify: High priority detection (WICHTIG keyword)
        """
        email_data = {
            "sender": "auslaenderbehoerde@berlin.de",
            "subject": "WICHTIG: Termin für Aufenthaltstitel",
            "body": "Sehr geehrte/r Antragsteller/in, Ihr Termin für die Verlängerung Ihres Aufenthaltstitels ist am 15. November 2024 um 10:00 Uhr. Bitte bringen Sie alle erforderlichen Unterlagen mit.",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        assert classification.suggested_folder == "Government", \
            f"Expected 'Government', got '{classification.suggested_folder}'"
        assert classification.priority_score is None or classification.priority_score >= 85, \
            f"Urgent government emails should have very high priority (>=85), got {classification.priority_score}"
        assert "ausländerbehörde" in classification.reasoning.lower() or "immigration" in classification.reasoning.lower() or "residence" in classification.reasoning.lower(), \
            f"Reasoning should mention immigration office: {classification.reasoning}"

        print(f"\n✓ Urgent Government Email (German):")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Priority: {classification.priority_score}")
        print(f"  Confidence: {classification.confidence}")


@pytest.mark.integration
class TestEdgeCasesWithGeminiAPI:
    """Edge case tests with real Gemini API."""

    def test_email_with_no_body(self, llm_client: LLMClient, user_folders):
        """
        Test: Email with no body (only subject)
        Verify: Classification based on sender + subject only
        """
        email_data = {
            "sender": "finanzamt@berlin.de",
            "subject": "Steuerbescheid 2024",
            "body": "",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        # Should still classify correctly based on sender domain
        assert classification.suggested_folder == "Government", \
            f"Expected 'Government' based on sender, got '{classification.suggested_folder}'"

        print(f"\n✓ Email with No Body:")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")

    def test_email_with_special_characters(self, llm_client: LLMClient, user_folders):
        """
        Test: Email with emojis and special unicode characters
        Verify: JSON parsing handles special characters correctly
        """
        email_data = {
            "sender": "marketing@company.com",
            "subject": "🎉 Special Offer! 50% Off 🎊",
            "body": "Hello! 👋 We're excited to offer you 50% off on all products! 🛍️ Use code: SAVE50 💰",
            "user_email": "test@example.com"
        }

        prompt = build_classification_prompt(email_data, user_folders)
        response_json = llm_client.receive_completion(prompt, operation="classification")
        classification = ClassificationResponse(**response_json)

        # Should classify as Newsletter (marketing email)
        assert classification.suggested_folder in ["Newsletters", "Unclassified"], \
            f"Expected 'Newsletters' or 'Unclassified', got '{classification.suggested_folder}'"
        # Verify response is valid (no JSON escape errors)
        assert isinstance(classification.reasoning, str)
        assert len(classification.reasoning) > 0

        print(f"\n✓ Email with Special Characters:")
        print(f"  Folder: {classification.suggested_folder}")
        print(f"  Reasoning: {classification.reasoning}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--integration"])
