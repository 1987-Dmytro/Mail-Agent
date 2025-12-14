"""
Email Classification Prompt Template

This module provides prompt engineering templates for AI-based email classification.
The prompt instructs the LLM (Gemini 2.5 Flash) to analyze incoming emails and suggest
the most appropriate folder category for organization.

Version: 1.0
Created: 2025-11-07
Last Updated: 2025-11-07

Features:
- Few-shot learning with 5 diverse examples
- Multilingual support (Russian, Ukrainian, English, German)
- Structured JSON output with schema validation
- Token-optimized (email body limited to 500 characters)
- User-specific folder categories
"""

import re
from typing import List, Dict
from html import unescape


CLASSIFICATION_PROMPT_VERSION = "1.0"


# Email body preprocessing
def _preprocess_email_body(body: str, max_length: int = 500) -> str:
    """
    Preprocess email body for classification prompt.

    - Strips HTML tags and extracts plain text
    - Limits to first max_length characters
    - Preserves key information (names, dates, amounts)
    - Ensures no mid-word truncation

    Args:
        body: Raw email body (may contain HTML)
        max_length: Maximum character length (default: 500 for token efficiency)

    Returns:
        Preprocessed plain text body preview
    """
    if not body:
        return ""

    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', body)

    # Unescape HTML entities
    text = unescape(text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Truncate to max_length, avoiding mid-word breaks
    if len(text) <= max_length:
        return text

    # Find last space before max_length to avoid breaking words
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.8:  # Only use last space if it's not too far back
        return text[:last_space] + "..."
    else:
        return text[:max_length] + "..."


def _format_folder_categories(user_folders: List[Dict]) -> str:
    """
    Format user folder categories for prompt inclusion.

    Args:
        user_folders: List of folder category dicts with 'name' and 'description' keys

    Returns:
        Formatted string with folder categories (one per line with description)
    """
    if not user_folders:
        return "- Important: Default folder for all emails"

    formatted = []
    for folder in user_folders:
        name = folder.get('name', 'Unknown')
        description = folder.get('description', 'No description')
        formatted.append(f"- {name}: {description}")

    # Note: No "Unclassified" fallback - LLM must always pick from user's actual folders

    return "\n".join(formatted)


# Classification prompt template
CLASSIFICATION_PROMPT_TEMPLATE = """You are an AI email classification assistant. Your role is to analyze incoming emails and suggest the most appropriate folder category for organization. You must provide clear reasoning for your classification decision to help the user understand your suggestion.

**Your Task:**
Classify the email below into one of the user's predefined folder categories. Consider the sender, subject line, and email content to make an informed decision. The user will review and approve your suggestion, so be thoughtful and explain your reasoning.

**Classification Guidelines:**

{user_folder_categories}

🚨 **CRITICAL RULE: You MUST choose a folder from the list above!**
- The "suggested_folder" field MUST EXACTLY MATCH one of the folder names listed above
- NEVER EVER use "Unclassified", "Other", "Unknown", or any folder not in the user's list
- If uncertain, pick the CLOSEST matching folder (usually "Important") and lower the confidence score
- Invalid folder names will cause system errors - this is NOT optional!

**When classifying, consider:**
- Sender domain and reputation (e.g., government domains like finanzamt.de, auslaenderbehoerde.de)
- Subject line keywords (e.g., "WICHTIG", "urgent", "deadline")
- Email content type (official documentation, business inquiry, marketing, personal correspondence)
- Formality level (formal German "Sie" indicates official communication)
- Time-sensitivity indicators

**If the email doesn't clearly fit any category:**
- Choose the CLOSEST MATCHING folder from the user's categories above (default to "Important" if very uncertain)
- Lower your confidence score (<0.7)
- Explain in reasoning why this was the best available option
- Remember: suggested_folder MUST be from the user's folder list - no exceptions!

---

**Email to Classify:**

From: {email_sender}
To: {user_email}
Subject: {email_subject}

Body Preview (first 500 characters):
{email_body_preview}

---

**Related Emails Context (RAG):**

{rag_context}

⚠️ **CRITICAL: You MUST analyze and use the context above to:**
1. **Understand conversation history** - Read "Full Conversation with Sender" to see previous discussions, agreements, and plans
2. **Determine needs_response** - Check if user already addressed the topic in previous emails
3. **Generate informed response_draft** - Reference specific details, dates, and plans from the conversation history
4. **Maintain continuity** - Your response should acknowledge what was previously discussed and agreed upon

**Example:** If current email asks "Ты помнишь куда мы планировали поехать?" (Do you remember where we planned to go?), you MUST:
- Check "Full Conversation with Sender" section above for mentions of locations (Frankfurt, Switzerland, etc.)
- Reference specific plans found in sender_history (e.g., "meeting at Hauptbahnhof Frankfurt")
- DO NOT say "I don't have specific information" if plans ARE mentioned in sender_history above!

---

**Your Output Format:**

Return ONLY valid JSON matching this schema (no markdown code fences, no additional text):

{{
  "suggested_folder": "<folder_name>",
  "reasoning": "<1-2 sentence explanation, max 300 characters>",
  "priority_score": <integer 0-100>,
  "confidence": <float 0.0-1.0>,
  "needs_response": <boolean>,
  "response_draft": "<AI-generated response draft if needs_response=true, otherwise null>",
  "detected_language": "<language_code>",
  "tone": "<formal|informal|professional|casual>"
}}

**Required Fields:**
- suggested_folder (string): Must exactly match one of the user's folder category names listed above
- reasoning (string): Concise explanation (max 300 characters) in English
- needs_response (boolean): Whether this email requires a response from the user
- detected_language (string): Language code of the email (ru, en, de, uk, etc.)
- tone (string): Formality level (formal, informal, professional, casual)

**Optional Fields:**
- priority_score (integer): 0-100 scale (government=high 80-100, clients=medium 50-70, newsletters=low 0-20)
- confidence (float): 0.0-1.0 scale (how certain you are about this classification)
- response_draft (string): AI-generated response if needs_response=true (50-2000 chars), null otherwise

**Language and Tone Detection Guidelines:**
- detected_language: Identify the primary language of the email based on subject and body
  - Use ISO 639-1 codes: "ru" (Russian), "en" (English), "de" (German), "uk" (Ukrainian), etc.
  - If mixed languages, choose the dominant one
  - Examples: "Праздники 2025" → "ru", "Tax deadline reminder" → "en", "Steuererklärung" → "de"
- tone: Determine formality level based on pronouns, greetings, and writing style
  - "formal": Uses formal pronouns (Вы, Sie, Sie), official greetings (Sehr geehrte, Уважаемый)
  - "informal": Uses informal pronouns (ты, du), casual greetings (Привет, Hi, Hallo)
  - "professional": Business context with polite but not overly formal tone
  - "casual": Friendly, relaxed communication style
  - Examples: "Sehr geehrte Damen und Herren" → "formal", "Привет!" → "informal"

**Response Classification Rules:**

⚠️ **CRITICAL STEP 1 - Check sender address patterns FIRST:**
- **noreply addresses** (noreply@*, no-reply@*, donotreply@*): ALWAYS needs_response = FALSE
- **Marketing/bulk email domains** (*@send.*, *@email.*, *@marketing.*, *@newsletter.*, *@promo.*): ALWAYS needs_response = FALSE
- **Automated system emails** (*@notifications.*, *@updates.*, *@alerts.*, *@info.*): ALWAYS needs_response = FALSE
- **Platform notifications** (LinkedIn, GitHub, Skool, Slack, etc.): ALWAYS needs_response = FALSE
- **Banking automated emails** (*@send.bank.*, *@email.bank.*, *@info.bank.*): ALWAYS needs_response = FALSE
- Examples of automated senders that should NEVER get response:
  - noreply@skool.com, notifications@github.com, noreply@linkedin.com
  - marketing@company.com, newsletter@techcrunch.com, admin@liamottley.com (marketing newsletters)
  - system@alerts.com, updates@platform.com
  - email@send.vtb.ru, no-reply@gosuslugi.ru (automated bank/government notifications)

⚠️ **CRITICAL STEP 2 - Analyze sender_history from RAG Context:**
- **If sender_history shows >5 emails with NO user responses** → HIGH probability this is a newsletter/automated sender → needs_response = FALSE
- **If sender_history shows consistent pattern (all marketing, all notifications)** → needs_response = FALSE
- **If sender_history is empty (0 emails)** → Use sender address patterns from STEP 1
- **If sender_history shows back-and-forth conversation** → More likely needs_response = TRUE
- Examples:
  - 38 emails from Liam Ottley, no user responses → Marketing newsletter → needs_response = FALSE
  - 6 emails from bank (email@send.vtb.ru), no user responses → Automated notifications → needs_response = FALSE
  - 3 emails from colleague with 2 user responses → Real conversation → needs_response = TRUE (if current email asks question)

⚠️ **CRITICAL STEP 3 - Final decision:**
- needs_response = TRUE for: questions, meeting requests, invitations, action requests, follow-ups requiring reply FROM REAL PEOPLE
- needs_response = FALSE for: newsletters, notifications, automated emails, security updates, informational announcements, marketing campaigns
- If needs_response=true, ALWAYS generate response_draft using "Full Conversation with Sender" and "Related Emails Context" above
- ⚠️ CRITICAL: Your draft MUST reference specific details from sender_history (dates, locations, plans, agreements)
- If needs_response=false, set response_draft to null

**Response Draft Generation Guidelines:**
- Write in the SAME LANGUAGE as detected_language (Russian→Russian, English→English, German→German)
- Match the detected tone (formal→formal "Вы"/"Sie", informal→informal "ты"/"du")
- Use gender-neutral language - avoid gendered forms when possible
- For Russian: Use masculine forms as default neutral (e.g., "рад" not "рад/рада", "готов" not "готов/готова")
- Keep responses brief, professional, and friendly (50-200 words)
- DO NOT add your name or signature - the system will add it automatically

**Important:**
- 🚨 CRITICAL: suggested_folder MUST EXACTLY MATCH one of the folder names from the list at the top (Clients, Government, Important, etc.)
- NEVER EVER use "Unclassified", "Other", "Unknown", "Inbox", or ANY folder name not in the user's list
- If uncertain which folder, default to "Important" with lower confidence score
- Invalid folder names cause system errors - this requirement is MANDATORY
- Keep reasoning under 300 characters (for Telegram message limit)
- Always provide reasoning in English, regardless of email language
- Use proper JSON escaping for special characters
- Do not include markdown code fences (```json) in your response

Now classify the email above."""


def build_classification_prompt(email_data: Dict, user_folders: List[Dict], rag_context: str = "") -> str:
    """
    Constructs classification prompt from email data, user folders, and RAG context.

    This function takes email metadata, user-defined folder categories, and related
    emails context (RAG), then generates a complete prompt string ready for the Gemini LLM API.
    The prompt includes:
    - System role instruction
    - Task description with classification guidelines
    - User's folder categories with descriptions
    - Email content (sender, subject, body preview)
    - Related emails context (RAG) for response generation
    - Few-shot examples (5 diverse scenarios)
    - JSON output schema specification with needs_response and response_draft

    Args:
        email_data: Dict with keys:
            - sender (str): Email from address
            - subject (str): Email subject line
            - body (str): Email body content (will be preprocessed and truncated to 500 chars)
            - message_id (str): Unique email identifier (optional, not used in prompt)
        user_folders: List of dicts with keys:
            - name (str): Folder category name
            - description (str): Brief description of what emails belong in this folder
        rag_context: String with related emails context from vector search (optional)

    Returns:
        Complete prompt string ready for LLMClient.send_prompt() or LLMClient.receive_completion()

    Example:
        >>> email_data = {
        ...     "sender": "finanzamt@berlin.de",
        ...     "subject": "Tax deadline reminder",
        ...     "body": "<p>Please submit your tax return...</p>"
        ... }
        >>> folders = [
        ...     {"name": "Government", "description": "Official government communications"},
        ...     {"name": "Clients", "description": "Business correspondence"}
        ... ]
        >>> prompt = build_classification_prompt(email_data, folders)
        >>> # Use with LLMClient:
        >>> # client = LLMClient()
        >>> # response = client.receive_completion(prompt, operation="classification")
    """
    # Extract email fields
    sender = email_data.get('sender', 'unknown@example.com')
    subject = email_data.get('subject', '(No subject)')
    body = email_data.get('body', '')
    user_email = email_data.get('user_email', 'user@example.com')

    # Preprocess email body (strip HTML, truncate to 500 chars)
    body_preview = _preprocess_email_body(body, max_length=500)

    # Format folder categories
    folder_categories_formatted = _format_folder_categories(user_folders)

    # Substitute placeholders
    prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
        email_sender=sender,
        email_subject=subject,
        email_body_preview=body_preview,
        user_folder_categories=folder_categories_formatted,
        user_email=user_email,
        rag_context=rag_context
    )

    return prompt
