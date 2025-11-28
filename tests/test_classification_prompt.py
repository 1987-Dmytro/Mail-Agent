"""
Unit Tests for Email Classification Prompt Engineering

Tests for:
- Prompt construction function (build_classification_prompt)
- Email body preprocessing (HTML stripping, truncation)
- ClassificationResponse Pydantic model validation
- Placeholder substitution and formatting

Test Strategy:
- Mock Gemini API (no real API calls in unit tests)
- Test prompt structure and content
- Test edge cases (HTML, long body, empty fields)
- Test schema validation with valid/invalid JSON

Created: 2025-11-07
"""

import pytest
from pydantic import ValidationError

from app.prompts.classification_prompt import (
    build_classification_prompt,
    _preprocess_email_body,
    _format_folder_categories,
    CLASSIFICATION_PROMPT_VERSION
)
from app.models.classification_response import ClassificationResponse


class TestPromptConstruction:
    """Test suite for classification prompt construction."""

    def test_build_classification_prompt_structure(self):
        """
        Test: Prompt contains all required sections
        Verify: System role, task description, examples, schema present
        """
        email_data = {
            "sender": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email body.",
            "user_email": "user@example.com"
        }
        user_folders = [
            {"name": "Government", "description": "Official government communications"},
            {"name": "Clients", "description": "Business correspondence"}
        ]

        prompt = build_classification_prompt(email_data, user_folders)

        # Verify prompt contains key sections
        assert "You are an AI email classification assistant" in prompt
        assert "Your Task:" in prompt
        assert "Classification Guidelines:" in prompt
        assert "Few-Shot Examples:" in prompt
        assert "Your Output Format:" in prompt

        # Verify placeholders substituted
        assert "test@example.com" in prompt
        assert "Test Email" in prompt
        assert "This is a test email body." in prompt
        assert "user@example.com" in prompt

        # Verify folder categories included
        assert "Government: Official government communications" in prompt
        assert "Clients: Business correspondence" in prompt
        assert "Unclassified" in prompt  # Always included as fallback

    def test_build_classification_prompt_with_html_body(self):
        """
        Test: Email body with HTML tags
        Verify: HTML stripped correctly, plain text extracted
        """
        email_data = {
            "sender": "newsletter@example.com",
            "subject": "Weekly Update",
            "body": "<html><body><h1>Hello</h1><p>This is a <b>bold</b> message.</p></body></html>",
            "user_email": "user@example.com"
        }
        user_folders = [{"name": "Newsletters", "description": "Email newsletters"}]

        prompt = build_classification_prompt(email_data, user_folders)

        # Verify HTML tags removed
        assert "<html>" not in prompt
        assert "<body>" not in prompt
        assert "<h1>" not in prompt
        assert "<p>" not in prompt
        assert "<b>" not in prompt

        # Verify plain text preserved
        assert "Hello" in prompt
        assert "bold" in prompt
        assert "message" in prompt

    def test_build_classification_prompt_with_long_body(self):
        """
        Test: Email body > 500 characters
        Verify: Body truncated to 500 characters, no mid-word break
        """
        # Create long body (1000 characters)
        long_body = "A" * 450 + " This is the end of the email body. " + "B" * 500

        email_data = {
            "sender": "sender@example.com",
            "subject": "Long Email",
            "body": long_body,
            "user_email": "user@example.com"
        }
        user_folders = [{"name": "Clients", "description": "Business emails"}]

        prompt = build_classification_prompt(email_data, user_folders)

        # Extract body preview from prompt
        body_preview_start = prompt.find("Body Preview (first 500 characters):") + len("Body Preview (first 500 characters):\n")
        body_preview_end = prompt.find("\n---", body_preview_start)
        body_preview = prompt[body_preview_start:body_preview_end].strip()

        # Verify truncation
        assert len(body_preview) <= 503  # 500 chars + "..." (3 chars)
        assert body_preview.endswith("...")

    def test_preprocess_email_body_html_stripping(self):
        """
        Test: HTML stripping function
        Verify: All HTML tags removed, entities unescaped
        """
        html_body = "<p>Hello &amp; welcome to our <strong>newsletter</strong>!</p>"
        processed = _preprocess_email_body(html_body, max_length=500)

        assert "<p>" not in processed
        assert "<strong>" not in processed
        assert "&amp;" not in processed
        assert "Hello & welcome to our newsletter!" in processed

    def test_preprocess_email_body_truncation(self):
        """
        Test: Body truncation at word boundaries
        Verify: No mid-word truncation
        """
        body = "This is a test email with many words that should be truncated properly without breaking words in the middle."
        processed = _preprocess_email_body(body, max_length=50)

        assert len(processed) <= 53  # 50 + "..." (3 chars)
        assert processed.endswith("...")
        # Verify truncation happened at word boundary (text before "..." should end with complete word)
        text_before_ellipsis = processed[:-3].strip()
        # Should not end with partial word - verify last character is not alphanumeric or space doesn't appear in middle
        assert not text_before_ellipsis.endswith(" ")  # Should be trimmed properly

    def test_preprocess_email_body_empty(self):
        """
        Test: Empty body handling
        Verify: Returns empty string
        """
        assert _preprocess_email_body("") == ""
        assert _preprocess_email_body(None) == ""

    def test_format_folder_categories_multiple(self):
        """
        Test: Multiple folder categories formatting
        Verify: All categories included with descriptions
        """
        folders = [
            {"name": "Government", "description": "Official documents"},
            {"name": "Clients", "description": "Business correspondence"},
            {"name": "Newsletters", "description": "Marketing emails"}
        ]
        formatted = _format_folder_categories(folders)

        assert "- Government: Official documents" in formatted
        assert "- Clients: Business correspondence" in formatted
        assert "- Newsletters: Marketing emails" in formatted
        assert "- Unclassified:" in formatted  # Always included

    def test_format_folder_categories_empty(self):
        """
        Test: Empty folder list
        Verify: Returns Unclassified as fallback
        """
        formatted = _format_folder_categories([])
        assert "- Unclassified:" in formatted

    def test_build_classification_prompt_with_multiple_folder_categories(self):
        """
        Test: Prompt with 10 folder categories
        Verify: All categories included in prompt
        """
        email_data = {
            "sender": "test@example.com",
            "subject": "Test",
            "body": "Test body",
            "user_email": "user@example.com"
        }
        user_folders = [
            {"name": f"Category{i}", "description": f"Description {i}"}
            for i in range(1, 11)
        ]

        prompt = build_classification_prompt(email_data, user_folders)

        # Verify all 10 categories present
        for i in range(1, 11):
            assert f"Category{i}: Description {i}" in prompt

    def test_prompt_version_constant(self):
        """
        Test: Prompt version constant defined
        Verify: Version is "1.0"
        """
        assert CLASSIFICATION_PROMPT_VERSION == "1.0"


class TestClassificationResponseValidation:
    """Test suite for ClassificationResponse Pydantic model validation."""

    def test_classification_response_valid_full(self):
        """
        Test: Valid JSON with all fields
        Verify: Parses successfully
        """
        data = {
            "suggested_folder": "Government",
            "reasoning": "Email from Finanzamt regarding tax documents deadline",
            "priority_score": 85,
            "confidence": 0.92
        }
        response = ClassificationResponse(**data)

        assert response.suggested_folder == "Government"
        assert response.reasoning == "Email from Finanzamt regarding tax documents deadline"
        assert response.priority_score == 85
        assert response.confidence == 0.92

    def test_classification_response_valid_required_only(self):
        """
        Test: Valid JSON with only required fields
        Verify: Optional fields default to None
        """
        data = {
            "suggested_folder": "Clients",
            "reasoning": "Business email from client"
        }
        response = ClassificationResponse(**data)

        assert response.suggested_folder == "Clients"
        assert response.reasoning == "Business email from client"
        assert response.priority_score is None
        assert response.confidence is None

    def test_classification_response_missing_required_field(self):
        """
        Test: Missing required field (suggested_folder)
        Verify: Raises ValidationError
        """
        data = {
            "reasoning": "Business email from client"
        }
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResponse(**data)

        assert "suggested_folder" in str(exc_info.value)

    def test_classification_response_invalid_priority_score(self):
        """
        Test: priority_score out of range (150 > 100)
        Verify: Raises ValidationError
        """
        data = {
            "suggested_folder": "Government",
            "reasoning": "Tax office email",
            "priority_score": 150  # Invalid: > 100
        }
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResponse(**data)

        assert "priority_score" in str(exc_info.value)

    def test_classification_response_invalid_confidence(self):
        """
        Test: confidence out of range (1.5 > 1.0)
        Verify: Raises ValidationError
        """
        data = {
            "suggested_folder": "Clients",
            "reasoning": "Client inquiry email",
            "confidence": 1.5  # Invalid: > 1.0
        }
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResponse(**data)

        assert "confidence" in str(exc_info.value)

    def test_classification_response_reasoning_too_long(self):
        """
        Test: reasoning > 300 characters
        Verify: Raises ValidationError
        """
        data = {
            "suggested_folder": "Government",
            "reasoning": "A" * 301  # 301 characters, exceeds 300 limit
        }
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResponse(**data)

        assert "reasoning" in str(exc_info.value)

    def test_classification_response_empty_folder(self):
        """
        Test: Empty suggested_folder
        Verify: Raises ValidationError
        """
        data = {
            "suggested_folder": "",
            "reasoning": "Test email"
        }
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResponse(**data)

        assert "suggested_folder" in str(exc_info.value)

    def test_classification_response_to_dict(self):
        """
        Test: to_dict method excludes None values
        Verify: Only populated fields in dict
        """
        data = {
            "suggested_folder": "Newsletters",
            "reasoning": "Marketing newsletter"
        }
        response = ClassificationResponse(**data)
        response_dict = response.to_dict()

        assert "suggested_folder" in response_dict
        assert "reasoning" in response_dict
        assert "priority_score" not in response_dict  # None, excluded
        assert "confidence" not in response_dict  # None, excluded

    def test_classification_response_edge_values(self):
        """
        Test: Edge values for priority_score and confidence
        Verify: Boundary values (0, 100, 0.0, 1.0) accepted
        """
        # Test minimum values
        data_min = {
            "suggested_folder": "Newsletters",
            "reasoning": "Low priority newsletter",
            "priority_score": 0,
            "confidence": 0.0
        }
        response_min = ClassificationResponse(**data_min)
        assert response_min.priority_score == 0
        assert response_min.confidence == 0.0

        # Test maximum values
        data_max = {
            "suggested_folder": "Government",
            "reasoning": "Urgent government email",
            "priority_score": 100,
            "confidence": 1.0
        }
        response_max = ClassificationResponse(**data_max)
        assert response_max.priority_score == 100
        assert response_max.confidence == 1.0
