"""Response generation prompt templates and formatting utilities.

This module provides structured templates for AI email response generation,
incorporating RAG context (thread history + semantic search results), tone detection,
and multilingual support across Russian, Ukrainian, English, and German.

Key Components:
- RESPONSE_PROMPT_TEMPLATE: Main template with placeholders for email content and context
- GREETING_EXAMPLES: Language × Tone matrix for appropriate email greetings
- CLOSING_EXAMPLES: Language × Tone matrix for appropriate email closings
- format_response_prompt: Function to format complete prompts ready for LLM consumption

Token Budget: ~6.5K tokens for context (leaves 25K for response generation in Gemini 32K window)
"""

from typing import Dict, List, Optional
from datetime import datetime


# Language name mappings for prompt instructions
LANGUAGE_NAMES: Dict[str, str] = {
    "de": "German",
    "en": "English",
    "ru": "Russian",
    "uk": "Ukrainian",
}


# Question indicators for needs_response detection (multilingual)
# Used by fallback classification when LLM is unavailable
QUESTION_INDICATORS: Dict[str, List[str]] = {
    "en": [
        "?",  # Question mark
        "what", "when", "where", "who", "why", "how",  # Question words
        "can you", "could you", "would you", "will you",  # Request patterns
        "please confirm", "please let me know", "please advise",  # Polite requests
    ],
    "de": [
        "?",  # Fragezeichen
        "was", "wann", "wo", "wer", "warum", "wie",  # Fragewörter
        "können sie", "könnten sie", "würden sie",  # Höfliche Bitten
        "bitte bestätigen", "bitte mitteilen", "bitte informieren",  # Höfliche Anfragen
    ],
    "ru": [
        "?",  # Вопросительный знак
        "что", "когда", "где", "кто", "почему", "как",  # Вопросительные слова
        "можешь", "можете", "мог бы", "могли бы",  # Модальные глаголы
        "подтверди", "ответь", "скажи", "уточни", "поясни",  # Императивные глаголы
        "пожалуйста подтверди", "пожалуйста сообщи",  # Вежливые просьбы
    ],
    "uk": [
        "?",  # Знак питання
        "що", "коли", "де", "хто", "чому", "як",  # Питальні слова
        "чи можеш", "чи можете", "чи міг би", "чи могли б",  # Модальні дієслова
        "підтверди", "відповідь", "скажи", "уточни", "поясни",  # Наказові дієслова
        "будь ласка підтверди", "будь ласка повідом",  # Ввічливі прохання
    ],
}


# Greeting examples: 4 languages × 3 tones = 12 combinations
GREETING_EXAMPLES: Dict[str, Dict[str, str]] = {
    "de": {
        "formal": "Sehr geehrte Damen und Herren",
        "professional": "Guten Tag {name}",
        "casual": "Hallo {name}",
    },
    "en": {
        "formal": "Dear Sir or Madam",
        "professional": "Hello {name}",
        "casual": "Hi {name}",
    },
    "ru": {
        "formal": "Уважаемые дамы и господа",
        "professional": "Здравствуйте, {name}",
        "casual": "Привет, {name}",
    },
    "uk": {
        "formal": "Шановні пані та панове",
        "professional": "Вітаю, {name}",
        "casual": "Привіт, {name}",
    },
}


# Closing examples: 4 languages × 3 tones = 12 combinations
CLOSING_EXAMPLES: Dict[str, Dict[str, str]] = {
    "de": {
        "formal": "Mit freundlichen Grüßen",
        "professional": "Beste Grüße",
        "casual": "Viele Grüße",
    },
    "en": {
        "formal": "Yours faithfully",
        "professional": "Best regards",
        "casual": "Cheers",
    },
    "ru": {
        "formal": "С уважением",
        "professional": "С наилучшими пожеланиями",
        "casual": "Всего хорошего",
    },
    "uk": {
        "formal": "З повагою",
        "professional": "З найкращими побажаннями",
        "casual": "Усього найкращого",
    },
}


# Response generation prompt template with all required placeholders
RESPONSE_PROMPT_TEMPLATE: str = """You are an AI email assistant helping to draft a response to an email.

ORIGINAL EMAIL:
From: {sender}
Subject: {subject}
Language: {language_name}
Body:
{email_body}

CONVERSATION CONTEXT:

Thread History (Chronological):
{thread_history}

Full Conversation History with Sender (Last 90 Days):
The following is the COMPLETE chronological history of ALL emails exchanged with this correspondent. Use this to understand the full context and timeline of your relationship.
{sender_history}

Relevant Context from Previous Emails (Semantic Search):
{semantic_results}

RESPONSE REQUIREMENTS:

1. Language: Write the response in {language_name} ({language_code})
2. Tone: {tone_description}
3. Length: 2-3 paragraphs maximum
4. Formality: {formality_instructions}

GREETING AND CLOSING EXAMPLES FOR THIS CONTEXT:

Appropriate Greeting: "{greeting_example}"
Appropriate Closing: "{closing_example}"

INSTRUCTIONS:

Please draft an email response that:
- Addresses the sender's main points and questions
- Maintains the appropriate tone ({tone}) and formality level
- Uses context from the conversation thread and relevant previous emails
- Follows the greeting/closing style shown above
- Is written entirely in {language_name}
- Is concise (2-3 paragraphs maximum)
- Sounds natural and professional

Generate the complete email response now:
"""


def format_response_prompt(
    email: "EmailProcessingQueue",  # type: ignore  # Forward reference to avoid circular import
    rag_context: Dict,  # RAGContext TypedDict from context_models.py
    language: str,
    tone: str,
) -> str:
    """Format a complete response generation prompt with all placeholders substituted.

    This function takes an email, RAG context (thread history + semantic results),
    detected language, and tone to construct a structured prompt ready for LLM consumption.

    Args:
        email: Email object containing sender, subject, body, etc.
        rag_context: RAGContext dict with thread_history and semantic_results lists
        language: Language code (de, en, ru, uk)
        tone: Detected tone (formal, professional, casual)

    Returns:
        Formatted prompt string ready to send to Gemini API

    Raises:
        ValueError: If language or tone is not supported
        KeyError: If rag_context is missing required keys

    Examples:
        >>> prompt = format_response_prompt(
        ...     email=email_obj,
        ...     rag_context={"thread_history": [...], "semantic_results": [...]},
        ...     language="de",
        ...     tone="formal"
        ... )
    """
    # Validate inputs
    if language not in LANGUAGE_NAMES:
        raise ValueError(f"Unsupported language: {language}. Supported: {list(LANGUAGE_NAMES.keys())}")

    if tone not in ["formal", "professional", "casual"]:
        raise ValueError(f"Unsupported tone: {tone}. Supported: formal, professional, casual")

    # Extract sender name (use first name if available, otherwise "there")
    sender_email = email.sender
    sender_name = sender_email.split("@")[0] if "@" in sender_email else "there"

    # Format thread history (chronological, with sender/date/body)
    thread_history_text = _format_thread_history(
        rag_context.get("thread_history", [])
    )

    # Format sender conversation history (ALL emails from sender, last 90 days)
    sender_history_text = _format_sender_history(
        rag_context.get("sender_history", [])
    )

    # Format semantic results (ranked by relevance, with similarity scores if available)
    semantic_results_text = _format_semantic_results(
        rag_context.get("semantic_results", [])
    )

    # Get greeting and closing examples for language+tone
    greeting_example = GREETING_EXAMPLES[language][tone].format(name=sender_name)
    closing_example = CLOSING_EXAMPLES[language][tone]

    # Prepare tone description and formality instructions
    tone_descriptions = {
        "formal": "Very formal and respectful (e.g., government correspondence)",
        "professional": "Professional and courteous (e.g., business communication)",
        "casual": "Friendly and conversational (e.g., personal correspondence)",
    }

    formality_instructions = {
        "formal": "Use formal language, avoid contractions, maintain distance and respect",
        "professional": "Use professional but approachable language, may use some contractions",
        "casual": "Use friendly, conversational language, contractions are fine",
    }

    # Get email body (EmailProcessingQueue doesn't store body, use subject as fallback)
    email_body = getattr(email, 'body', None) or email.subject or "No body available"

    # Substitute all template placeholders
    formatted_prompt = RESPONSE_PROMPT_TEMPLATE.format(
        sender=email.sender,
        subject=email.subject,
        language_name=LANGUAGE_NAMES[language],
        language_code=language,
        email_body=email_body[:2000],  # Limit body to prevent token overflow
        thread_history=thread_history_text,
        sender_history=sender_history_text,  # NEW: Full sender conversation history
        semantic_results=semantic_results_text,
        tone_description=tone_descriptions[tone],
        formality_instructions=formality_instructions[tone],
        greeting_example=greeting_example,
        closing_example=closing_example,
        tone=tone,
    )

    return formatted_prompt


def _format_thread_history(thread_history: List[Dict]) -> str:
    """Format thread history into chronological text with sender/date/body.

    Args:
        thread_history: List of EmailMessage dicts from RAG context

    Returns:
        Formatted string with thread history, or "No thread history available" if empty
    """
    if not thread_history:
        return "No thread history available."

    formatted_entries = []
    for i, email_msg in enumerate(thread_history, 1):
        sender = email_msg.get("sender", "Unknown")
        date = email_msg.get("date", "Unknown date")  # FIX: was "sent_at"
        body = email_msg.get("body", "")

        # Format date if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d %H:%M")

        formatted_entries.append(
            f"{i}. From: {sender} | Date: {date}\n   {body[:300]}..."  # Limit each email to 300 chars
        )

    return "\n\n".join(formatted_entries)


def _format_sender_history(sender_history: List[Dict]) -> str:
    """Format sender conversation history into chronological timeline.

    Args:
        sender_history: List of ALL EmailMessage dicts from sender (90 days)

    Returns:
        Formatted chronological timeline, or "No sender history available" if empty
    """
    if not sender_history:
        return "No sender history available."

    formatted_entries = []
    for i, email_msg in enumerate(sender_history, 1):
        sender = email_msg.get("sender", "Unknown")
        subject = email_msg.get("subject", "No Subject")
        date = email_msg.get("date", "Unknown date")
        body = email_msg.get("body", "")

        # Format date if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d %H:%M")

        formatted_entries.append(
            f"{i}. [{date}] {subject}\n   From: {sender}\n   {body[:200]}..."
        )

    return "\n\n".join(formatted_entries)


def _format_semantic_results(semantic_results: List[Dict]) -> str:
    """Format semantic search results ranked by relevance.

    Args:
        semantic_results: List of EmailMessage dicts with similarity scores

    Returns:
        Formatted string with semantic results, or "No relevant context found" if empty
    """
    if not semantic_results:
        return "No relevant context found from previous emails."

    formatted_entries = []
    for i, email_msg in enumerate(semantic_results, 1):
        sender = email_msg.get("sender", "Unknown")
        date = email_msg.get("date", "Unknown date")  # FIX: was "sent_at"
        body = email_msg.get("body", "")
        similarity = email_msg.get("similarity_score", 0.0)

        # Format date if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")

        formatted_entries.append(
            f"{i}. Relevance: {similarity:.2f} | From: {sender} | Date: {date}\n   {body[:250]}..."
        )

    return "\n\n".join(formatted_entries)
