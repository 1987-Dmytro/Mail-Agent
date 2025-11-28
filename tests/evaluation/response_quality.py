"""
Response Quality Evaluation Framework

This module provides comprehensive evaluation of generated email responses across three dimensions:
1. Language Accuracy (40% weight) - Verifies response is in the expected language
2. Tone Appropriateness (30% weight) - Verifies greeting, closing, and formality match expected tone
3. Context Awareness (30% weight) - Verifies response references thread history and addresses key topics

Used in Story 3.10 multilingual response quality testing to validate AC #3.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import re


@dataclass
class LanguageScore:
    """Language detection score for a response"""
    detected_language: str
    confidence: float
    score: int  # 0-100
    matches_expected: bool
    details: str


@dataclass
class ToneScore:
    """Tone appropriateness score for a response"""
    detected_tone: str
    formality_level: str
    score: int  # 0-100
    matches_expected: bool
    greeting_appropriate: bool
    closing_appropriate: bool
    details: str


@dataclass
class ContextScore:
    """Context awareness score for a response"""
    score: int  # 0-100
    matched_keywords: List[str]
    references_thread: bool
    addresses_inquiry: bool
    details: str


@dataclass
class ResponseQualityReport:
    """
    Comprehensive quality report for a generated response.

    Overall score is weighted average:
    - Language: 40%
    - Tone: 30%
    - Context: 30%

    Acceptable threshold: 80% (90% for government emails)
    """
    language_score: LanguageScore
    tone_score: ToneScore
    context_score: ContextScore
    overall_score: int  # 0-100
    is_acceptable: bool
    threshold: int

    def generate_report(self) -> Dict[str, Any]:
        """Generate detailed report dictionary"""
        return {
            "overall_score": self.overall_score,
            "is_acceptable": self.is_acceptable,
            "threshold": self.threshold,
            "language": {
                "score": self.language_score.score,
                "detected": self.language_score.detected_language,
                "confidence": self.language_score.confidence,
                "matches_expected": self.language_score.matches_expected,
                "details": self.language_score.details
            },
            "tone": {
                "score": self.tone_score.score,
                "detected": self.tone_score.detected_tone,
                "formality": self.tone_score.formality_level,
                "matches_expected": self.tone_score.matches_expected,
                "greeting_ok": self.tone_score.greeting_appropriate,
                "closing_ok": self.tone_score.closing_appropriate,
                "details": self.tone_score.details
            },
            "context": {
                "score": self.context_score.score,
                "matched_keywords": self.context_score.matched_keywords,
                "references_thread": self.context_score.references_thread,
                "addresses_inquiry": self.context_score.addresses_inquiry,
                "details": self.context_score.details
            }
        }


def evaluate_language_accuracy(response: str, expected_language: str) -> LanguageScore:
    """
    Evaluate if response is in the expected language using langdetect.

    Args:
        response: Generated response text
        expected_language: Expected language code (ru, uk, en, de)

    Returns:
        LanguageScore with detection results and score (0-100)

    Score calculation:
    - Correct language + high confidence (>0.9): 100
    - Correct language + medium confidence (0.7-0.9): 90
    - Correct language + low confidence (<0.7): 80
    - Wrong language: 0
    """
    try:
        from langdetect import detect, detect_langs

        # Detect language
        detected = detect(response)

        # Get confidence
        langs = detect_langs(response)
        confidence = 0.0
        for lang in langs:
            if lang.lang == detected:
                confidence = lang.prob
                break

        # Check if matches expected
        matches = (detected == expected_language)

        # Calculate score
        if matches:
            if confidence >= 0.9:
                score = 100
            elif confidence >= 0.7:
                score = 90
            else:
                score = 80
        else:
            score = 0

        details = f"Detected {detected} with {confidence:.2f} confidence (expected {expected_language})"

        return LanguageScore(
            detected_language=detected,
            confidence=confidence,
            score=score,
            matches_expected=matches,
            details=details
        )

    except Exception as e:
        # Fallback if detection fails (e.g., too short text)
        return LanguageScore(
            detected_language="unknown",
            confidence=0.0,
            score=0,
            matches_expected=False,
            details=f"Language detection failed: {str(e)}"
        )


def evaluate_tone_appropriateness(
    response: str,
    expected_tone: str,
    language: str,
    expected_criteria: Dict[str, Any] = None
) -> ToneScore:
    """
    Evaluate if response tone (greeting, closing, formality) matches expected.

    Args:
        response: Generated response text
        expected_tone: Expected tone (formal, professional, casual)
        language: Response language (ru, uk, en, de)
        expected_criteria: Optional dict with tone_markers including:
            - greeting_examples: List of acceptable greetings
            - closing_examples: List of acceptable closings
            - required_greeting: Exact required greeting (for formal German government)
            - required_closing: Exact required closing (for formal German government)

    Returns:
        ToneScore with evaluation results (0-100)

    Score calculation:
    - Appropriate greeting + closing + formality: 100
    - Appropriate greeting OR closing + formality: 70
    - Formality ok but greeting/closing missing: 50
    - Wrong tone: 30
    - Missing greeting and closing: 0
    """
    response_lower = response.lower()
    score = 0
    greeting_ok = False
    closing_ok = False
    formality_match = False

    # Extract criteria
    if expected_criteria:
        greeting_examples = expected_criteria.get("greeting_examples", [])
        closing_examples = expected_criteria.get("closing_examples", [])
        required_greeting = expected_criteria.get("required_greeting")
        required_closing = expected_criteria.get("required_closing")
    else:
        greeting_examples = []
        closing_examples = []
        required_greeting = None
        required_closing = None

    # Check for required greeting (strict match for formal German government emails)
    if required_greeting:
        if required_greeting.lower() in response_lower:
            greeting_ok = True
        else:
            # For government emails, missing required greeting is critical
            score = 0
            details = f"REQUIRED greeting '{required_greeting}' not found (formal German government email)"
            return ToneScore(
                detected_tone=expected_tone,
                formality_level="very-high",
                score=score,
                matches_expected=False,
                greeting_appropriate=False,
                closing_appropriate=closing_ok,
                details=details
            )
    elif greeting_examples:
        # Check if any greeting example is present
        for greeting in greeting_examples:
            if greeting.lower() in response_lower:
                greeting_ok = True
                break

    # Check for required closing (strict match for formal German government emails)
    if required_closing:
        if required_closing.lower() in response_lower:
            closing_ok = True
        else:
            # For government emails, missing required closing is critical
            score = max(score, 40)  # Partial credit if greeting was ok
            details = f"REQUIRED closing '{required_closing}' not found (formal German government email)"
            return ToneScore(
                detected_tone=expected_tone,
                formality_level="very-high",
                score=score,
                matches_expected=False,
                greeting_appropriate=greeting_ok,
                closing_appropriate=False,
                details=details
            )
    elif closing_examples:
        # Check if any closing example is present
        for closing in closing_examples:
            if closing.lower() in response_lower:
                closing_ok = True
                break

    # Assess formality level (simple heuristics)
    formal_indicators = ["sehr geehrte", "dear sir", "уважаемый", "шановн"]
    professional_indicators = ["best regards", "с уважением", "з повагою", "mit freundlichen"]
    casual_indicators = ["hey", "hi", "привет", "привіт", "cheers"]

    has_formal = any(indicator in response_lower for indicator in formal_indicators)
    has_professional = any(indicator in response_lower for indicator in professional_indicators)
    has_casual = any(indicator in response_lower for indicator in casual_indicators)

    # Determine detected formality
    if has_formal or (expected_tone == "formal" and (greeting_ok or closing_ok)):
        detected_formality = "high"
        formality_match = (expected_tone == "formal")
    elif has_professional or (expected_tone == "professional" and (greeting_ok or closing_ok)):
        detected_formality = "medium"
        formality_match = (expected_tone in ["professional", "formal"])
    elif has_casual:
        detected_formality = "low"
        formality_match = (expected_tone == "casual")
    else:
        detected_formality = "unknown"
        formality_match = False

    # Calculate score
    if greeting_ok and closing_ok and formality_match:
        score = 100
    elif (greeting_ok or closing_ok) and formality_match:
        score = 70
    elif formality_match:
        score = 50
    elif greeting_ok or closing_ok:
        score = 30
    else:
        score = 0

    # Build details
    parts = []
    if greeting_ok:
        parts.append("greeting ✓")
    else:
        parts.append("greeting ✗")
    if closing_ok:
        parts.append("closing ✓")
    else:
        parts.append("closing ✗")
    if formality_match:
        parts.append(f"formality {detected_formality} ✓")
    else:
        parts.append(f"formality {detected_formality} ✗ (expected {expected_tone})")
    details = ", ".join(parts)

    return ToneScore(
        detected_tone=expected_tone if formality_match else "mismatch",
        formality_level=detected_formality,
        score=score,
        matches_expected=(greeting_ok and closing_ok and formality_match),
        greeting_appropriate=greeting_ok,
        closing_appropriate=closing_ok,
        details=details
    )


def evaluate_context_awareness(
    response: str,
    expected_context_keywords: List[str],
    expected_criteria: Dict[str, Any] = None
) -> ContextScore:
    """
    Evaluate if response demonstrates awareness of conversation context.

    Args:
        response: Generated response text
        expected_context_keywords: Keywords that should appear in contextually aware response
        expected_criteria: Optional dict with:
            - should_reference_thread: bool
            - key_topics_to_address: List[str]

    Returns:
        ContextScore with evaluation results (0-100)

    Score calculation:
    - All keywords present + addresses topics: 100
    - >50% keywords + addresses topics: 80
    - Some keywords (>25%): 60
    - Few keywords: 40
    - No keywords: 0
    """
    response_lower = response.lower()
    matched_keywords = []

    # Check keyword matches
    for keyword in expected_context_keywords:
        if keyword.lower() in response_lower:
            matched_keywords.append(keyword)

    # Calculate keyword match rate
    if expected_context_keywords:
        match_rate = len(matched_keywords) / len(expected_context_keywords)
    else:
        match_rate = 0.0

    # Extract additional criteria
    should_reference_thread = False
    key_topics = []
    if expected_criteria:
        should_reference_thread = expected_criteria.get("should_reference_thread", False)
        key_topics = expected_criteria.get("key_topics_to_address", [])

    # Check if key topics are addressed
    topics_addressed = 0
    for topic in key_topics:
        # Simple substring check (could be enhanced with semantic matching)
        topic_words = topic.lower().split()
        if any(word in response_lower for word in topic_words):
            topics_addressed += 1

    topics_address_rate = topics_addressed / len(key_topics) if key_topics else 1.0

    # Calculate score
    if match_rate >= 0.75 and topics_address_rate >= 0.75:
        score = 100
    elif match_rate >= 0.5 and topics_address_rate >= 0.5:
        score = 80
    elif match_rate >= 0.25:
        score = 60
    elif match_rate > 0:
        score = 40
    else:
        score = 0

    # Build details
    details = (
        f"Keywords: {len(matched_keywords)}/{len(expected_context_keywords)} matched "
        f"({match_rate*100:.0f}%), Topics: {topics_addressed}/{len(key_topics)} addressed "
        f"({topics_address_rate*100:.0f}%)"
    )

    return ContextScore(
        score=score,
        matched_keywords=matched_keywords,
        references_thread=(len(matched_keywords) > 0),
        addresses_inquiry=(topics_address_rate >= 0.5),
        details=details
    )


def evaluate_response_quality(
    response: str,
    expected_criteria: Dict[str, Any]
) -> ResponseQualityReport:
    """
    Evaluate overall response quality across language, tone, and context dimensions.

    Args:
        expected_criteria: Dictionary containing:
            - language_markers: {language_code, greeting_examples, closing_examples}
            - tone_markers: {tone, formality_level, expected_phrases}
            - context_awareness: {should_reference_thread, key_topics_to_address, relevant_keywords}
            - quality_threshold: int (default 80, use 90 for government emails)

    Returns:
        ResponseQualityReport with aggregated scores and acceptability verdict

    Scoring weights:
    - Language: 40%
    - Tone: 30%
    - Context: 30%
    """
    # Extract criteria
    language_markers = expected_criteria.get("language_markers", {})
    tone_markers = expected_criteria.get("tone_markers", {})
    context_criteria = expected_criteria.get("context_awareness", {})
    threshold = expected_criteria.get("quality_threshold", 80)

    # Evaluate each dimension
    lang_score = evaluate_language_accuracy(
        response,
        language_markers.get("language_code", "en")
    )

    tone_score = evaluate_tone_appropriateness(
        response,
        tone_markers.get("tone", "professional"),
        language_markers.get("language_code", "en"),
        expected_criteria=language_markers
    )

    ctx_score = evaluate_context_awareness(
        response,
        context_criteria.get("relevant_keywords", []),
        expected_criteria=context_criteria
    )

    # Calculate weighted overall score
    overall = int(
        lang_score.score * 0.40 +
        tone_score.score * 0.30 +
        ctx_score.score * 0.30
    )

    # Check acceptability
    acceptable = (overall >= threshold)

    return ResponseQualityReport(
        language_score=lang_score,
        tone_score=tone_score,
        context_score=ctx_score,
        overall_score=overall,
        is_acceptable=acceptable,
        threshold=threshold
    )
