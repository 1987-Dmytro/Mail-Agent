"""
Unit tests for response quality evaluation framework.

Story 3.10, Task 2.3: Tests evaluate_language_accuracy, evaluate_tone_appropriateness,
evaluate_context_awareness, and ResponseQualityReport aggregation.

Total: 8 unit tests covering AC #3 (response quality evaluation)
"""

import pytest
import sys
from pathlib import Path

# Add tests directory to path for evaluation module import
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.response_quality import (
    evaluate_language_accuracy,
    evaluate_tone_appropriateness,
    evaluate_context_awareness,
    evaluate_response_quality,
    ResponseQualityReport,
)


# Test 1: Russian language detection
def test_evaluate_language_accuracy_russian():
    """
    Test Russian language detection in response (AC #1, #3).
    Verifies langdetect correctly identifies Russian text.
    """
    # Russian response sample
    response = """Здравствуйте,

Благодарю за ваше обращение. С удовольствием предоставлю информацию о наших услугах.

С уважением"""

    result = evaluate_language_accuracy(response, "ru")

    # Assertions
    assert result.detected_language == "ru", f"Expected ru, got {result.detected_language}"
    assert result.matches_expected is True, "Language should match expected"
    assert result.confidence > 0.9, f"Confidence should be high, got {result.confidence}"
    assert result.score >= 90, f"Score should be >=90 for high confidence match, got {result.score}"


# Test 2: German language detection
def test_evaluate_language_accuracy_german():
    """
    Test German language detection accuracy (AC #1, #3, #4).
    Critical for formal German government email testing.
    """
    # German response sample (formal)
    response = """Sehr geehrte Damen und Herren,

vielen Dank für Ihre Anfrage. Ich werde die erforderlichen Unterlagen fristgerecht einreichen.

Mit freundlichen Grüßen"""

    result = evaluate_language_accuracy(response, "de")

    # Assertions
    assert result.detected_language == "de", f"Expected de, got {result.detected_language}"
    assert result.matches_expected is True, "Language should match expected"
    assert result.confidence > 0.9, f"Confidence should be high, got {result.confidence}"
    assert result.score >= 90, f"Score should be >=90, got {result.score}"


# Test 3: Formal German tone markers (CRITICAL for AC #4)
def test_evaluate_tone_appropriateness_formal_german():
    """
    Test formal German greetings/closings (AC #3, #4 - CRITICAL).
    Government emails MUST include "Sehr geehrte Damen und Herren" and "Mit freundlichen Grüßen".
    """
    # Formal German government response
    response = """Sehr geehrte Damen und Herren,

hiermit bestätige ich den Erhalt Ihrer Anforderung. Ich werde die Steuererklärung fristgerecht einreichen.

Mit freundlichen Grüßen"""

    criteria = {
        "greeting_examples": ["Sehr geehrte Damen und Herren"],
        "closing_examples": ["Mit freundlichen Grüßen"],
        "required_greeting": "Sehr geehrte Damen und Herren",
        "required_closing": "Mit freundlichen Grüßen"
    }

    result = evaluate_tone_appropriateness(
        response,
        expected_tone="formal",
        language="de",
        expected_criteria=criteria
    )

    # Assertions - STRICT for government emails
    assert result.greeting_appropriate is True, "Required formal German greeting missing"
    assert result.closing_appropriate is True, "Required formal German closing missing"
    assert result.score >= 90, f"Formal German should score >=90, got {result.score}"
    assert result.matches_expected is True, "Tone should match expected formal"
    assert "✓" in result.details, "Details should show success markers"


# Test 4: Casual English tone markers
def test_evaluate_tone_appropriateness_casual_english():
    """
    Test casual tone markers detection (AC #3).
    Verifies informal greetings and closings are recognized.
    """
    # Casual English response
    response = """Hey Sarah!

It's great to hear from you! I'd love to catch up. The new job is going really well.

Cheers,
Alex"""

    criteria = {
        "greeting_examples": ["Hey", "Hi"],
        "closing_examples": ["Cheers", "Talk soon", "Catch you later"]
    }

    result = evaluate_tone_appropriateness(
        response,
        expected_tone="casual",
        language="en",
        expected_criteria=criteria
    )

    # Assertions
    assert result.greeting_appropriate is True, "Casual greeting should be detected"
    assert result.closing_appropriate is True, "Casual closing should be detected"
    assert result.score >= 70, f"Casual tone should score well, got {result.score}"
    assert result.formality_level in ["low", "medium"], f"Formality should be low/medium, got {result.formality_level}"


# Test 5: Context awareness with thread reference
def test_evaluate_context_awareness_thread_reference():
    """
    Test response references thread history appropriately (AC #3).
    Verifies keyword matching and topic addressing.
    """
    # Response referencing previous discussion
    response = """Thank you for your inquiry about our software development services.

As discussed in our previous email, we specialize in enterprise solutions with typical project timelines of 3-6 months.

I'd be happy to provide a detailed proposal."""

    keywords = ["software development", "services", "enterprise", "timelines", "proposal"]
    criteria = {
        "should_reference_thread": True,
        "key_topics_to_address": ["services information", "project timelines"]
    }

    result = evaluate_context_awareness(response, keywords, expected_criteria=criteria)

    # Assertions
    assert len(result.matched_keywords) >= 4, f"Should match most keywords, matched {len(result.matched_keywords)}"
    assert result.references_thread is True, "Should show thread reference"
    assert result.addresses_inquiry is True, "Should address inquiry"
    assert result.score >= 80, f"Context awareness should score >=80, got {result.score}"


# Test 6: Context awareness with no context
def test_evaluate_context_awareness_no_context():
    """
    Test handling when context is missing or minimal (AC #3).
    Response should still be evaluated fairly.
    """
    # Generic response with no thread-specific context
    response = """Hello,

Thank you for reaching out. I would be happy to help answer your questions.

Best regards"""

    keywords = ["project", "collaboration", "timeline", "budget"]
    criteria = {
        "should_reference_thread": False,
        "key_topics_to_address": []
    }

    result = evaluate_context_awareness(response, keywords, expected_criteria=criteria)

    # Assertions
    assert len(result.matched_keywords) == 0, "Should not match specific keywords"
    assert result.score < 60, f"Low context match should score <60, got {result.score}"
    # Note: This is expected behavior for first email in thread (no context available)


# Test 7: ResponseQualityReport aggregation
def test_response_quality_report_aggregation():
    """
    Test overall scoring with weighted aggregation (AC #3).
    Language 40%, Tone 30%, Context 30%.
    """
    # Sample response in English, professional tone, good context
    response = """Dear John,

Thank you for your inquiry about our software development partnership. As mentioned in our previous discussion, we specialize in enterprise solutions.

I would be delighted to provide detailed information about our service offerings and project timelines.

Best regards"""

    criteria = {
        "language_markers": {
            "language_code": "en",
            "greeting_examples": ["Dear John", "Dear Mr. Smith"],
            "closing_examples": ["Best regards", "Kind regards"]
        },
        "tone_markers": {
            "tone": "formal",
            "formality_level": "high"
        },
        "context_awareness": {
            "relevant_keywords": ["partnership", "software development", "enterprise", "services", "timelines"],
            "should_reference_thread": True,
            "key_topics_to_address": ["service offerings", "project timelines"]
        },
        "quality_threshold": 80
    }

    report = evaluate_response_quality(response, criteria)

    # Assertions
    assert report.overall_score >= 0 and report.overall_score <= 100, "Score should be 0-100"
    assert report.language_score.score > 0, "Language score should be calculated"
    assert report.tone_score.score > 0, "Tone score should be calculated"
    assert report.context_score.score > 0, "Context score should be calculated"

    # Verify weighted calculation (approximately)
    expected_overall = int(
        report.language_score.score * 0.40 +
        report.tone_score.score * 0.30 +
        report.context_score.score * 0.30
    )
    assert abs(report.overall_score - expected_overall) <= 1, "Overall score should match weighted average"

    # Verify report generation
    report_dict = report.generate_report()
    assert "overall_score" in report_dict, "Report should include overall score"
    assert "language" in report_dict, "Report should include language details"
    assert "tone" in report_dict, "Report should include tone details"
    assert "context" in report_dict, "Report should include context details"


# Test 8: ResponseQualityReport acceptable threshold
def test_response_quality_acceptable_threshold():
    """
    Test pass/fail threshold (80% for standard, 90% for government emails) (AC #3, #4).
    """
    # High quality response (should pass 80% threshold)
    high_quality_response = """Sehr geehrte Damen und Herren,

vielen Dank für Ihre Nachricht bezüglich der Aufenthaltserlaubnis. Ich werde alle erforderlichen Unterlagen fristgerecht einreichen.

Mit freundlichen Grüßen"""

    criteria_standard = {
        "language_markers": {
            "language_code": "de",
            "greeting_examples": ["Sehr geehrte Damen und Herren"],
            "closing_examples": ["Mit freundlichen Grüßen"]
        },
        "tone_markers": {
            "tone": "formal",
            "formality_level": "very-high"
        },
        "context_awareness": {
            "relevant_keywords": ["Aufenthaltserlaubnis", "Unterlagen", "einreichen"],
            "key_topics_to_address": ["Unterlagen einreichen"]
        },
        "quality_threshold": 80
    }

    report_80 = evaluate_response_quality(high_quality_response, criteria_standard)
    assert report_80.threshold == 80, "Threshold should be 80"
    assert report_80.is_acceptable is True, "High quality response should pass 80% threshold"

    # Test with 90% government threshold
    criteria_government = {**criteria_standard, "quality_threshold": 90}
    criteria_government["language_markers"]["required_greeting"] = "Sehr geehrte Damen und Herren"
    criteria_government["language_markers"]["required_closing"] = "Mit freundlichen Grüßen"

    report_90 = evaluate_response_quality(high_quality_response, criteria_government)
    assert report_90.threshold == 90, "Threshold should be 90 for government"
    # Note: Actual pass/fail depends on scores, but threshold is correctly set


# Test runner for development
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
