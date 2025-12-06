"""Telegram message formatting service for email sorting proposals.

This module provides functions to format email sorting proposals with visual hierarchy
and create inline keyboards for user approval actions.
"""

from telegram import InlineKeyboardButton


def format_sorting_proposal_message(
    sender: str,
    subject: str,
    body_preview: str,
    proposed_folder: str,
    reasoning: str,
    is_priority: bool = False,
    needs_response: bool = False,
    has_draft: bool = False
) -> str:
    """Format email sorting proposal message with visual hierarchy.

    Creates a Telegram message showing email preview and AI sorting suggestion,
    formatted with Markdown for clear visual hierarchy.

    Args:
        sender: Email sender address or name
        subject: Email subject line
        body_preview: First portion of email body (will be truncated to 100 chars)
        proposed_folder: AI-suggested folder name for sorting
        reasoning: AI reasoning for the suggestion (1-2 sentences)
        is_priority: Whether this is a priority email (triggers ⚠️ icon)
        needs_response: Whether AI determined this email needs a response
        has_draft: Whether a response draft is available

    Returns:
        Formatted message string with Markdown markup

    Example:
        >>> format_sorting_proposal_message(
        ...     sender="finanzamt@berlin.de",
        ...     subject="Tax Documents Required",
        ...     body_preview="Dear taxpayer, we require...",
        ...     proposed_folder="Government",
        ...     reasoning="Email from German tax office regarding documents.",
        ...     is_priority=True,
        ...     needs_response=True,
        ...     has_draft=True
        ... )
        '⚠️ **New Email Sorting Proposal**\\n\\n**From:** finanzamt@berlin.de...'
    """
    priority_icon = "⚠️ " if is_priority else ""

    # Truncate body preview to exactly 100 characters
    truncated_preview = body_preview[:100]
    if len(body_preview) > 100:
        truncated_preview += "..."

    # Format needs_response indicator
    if needs_response:
        response_line = "\n✉️ **Requires Response:** Yes"
        if has_draft:
            response_line += " (draft available)"
    else:
        response_line = "\n📭 **Requires Response:** No"

    message = f"""{priority_icon}**New Email Sorting Proposal**

**From:** {sender}
**Subject:** {subject}

**Preview:** {truncated_preview}

**AI Suggests:** Sort to "{proposed_folder}"
**Reasoning:** {reasoning}{response_line}

What would you like to do?"""

    return message


def create_inline_keyboard(email_id: int) -> list[list[InlineKeyboardButton]]:
    """Create inline keyboard with approval buttons for sorting proposal.

    Creates a Telegram inline keyboard with three action buttons:
    - Approve: Accept AI suggestion and apply proposed folder
    - Change Folder: Open folder selection menu to choose different folder
    - Reject: Decline proposal, leave email in inbox

    The callback_data format enables the Telegram callback handler to reconnect
    to the correct workflow instance via WorkflowMapping lookup.

    Args:
        email_id: Email processing queue ID for workflow reconnection

    Returns:
        2D list of InlineKeyboardButton objects (compatible with TelegramBotClient.send_message_with_buttons)

    Callback Data Format:
        - approve_{email_id}: User approves AI suggestion
        - change_{email_id}: User wants to select different folder
        - reject_{email_id}: User rejects proposal

    Example:
        >>> keyboard = create_inline_keyboard(email_id=42)
        >>> # Renders as:
        >>> # [✅ Approve] [📁 Change Folder]
        >>> #        [❌ Reject]
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{email_id}"),
            InlineKeyboardButton("📁 Change Folder", callback_data=f"change_{email_id}"),
        ],
        [
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{email_id}"),
        ]
    ]
    return keyboard


def format_response_draft_message(
    sender: str,
    subject: str,
    draft_response: str,
    detected_language: str = None,
    tone: str = None
) -> str:
    """Format response draft notification message for user approval.

    Creates a Telegram message showing the AI-generated response draft
    that the user can Send, Edit, or Reject.

    Args:
        sender: Email sender address (recipient of the response)
        subject: Original email subject line
        draft_response: AI-generated response draft text
        detected_language: Detected language code (ru, en, de, etc.)
        tone: Detected tone/formality (formal, informal, professional, casual)

    Returns:
        Formatted message string with Markdown markup

    Example:
        >>> format_response_draft_message(
        ...     sender="friend@example.com",
        ...     subject="Meeting tomorrow",
        ...     draft_response="Hi! Yes, I'd be happy to meet tomorrow...",
        ...     detected_language="en",
        ...     tone="informal"
        ... )
        '📧 **Response Draft Ready**\\n\\n...'
    """
    # Truncate draft if too long (Telegram message limit ~4000 chars)
    max_draft_length = 1500
    truncated_draft = draft_response
    if len(draft_response) > max_draft_length:
        truncated_draft = draft_response[:max_draft_length] + "\n\n...(truncated)"

    # Format language and tone info
    metadata_line = ""
    if detected_language or tone:
        metadata_parts = []
        if detected_language:
            lang_names = {"ru": "Russian", "en": "English", "de": "German", "uk": "Ukrainian"}
            lang_display = lang_names.get(detected_language, detected_language.upper())
            metadata_parts.append(f"Language: {lang_display}")
        if tone:
            metadata_parts.append(f"Tone: {tone.capitalize()}")
        metadata_line = "\n📝 **Draft Info:** " + " | ".join(metadata_parts)

    message = f"""📧 **Response Draft Ready**

📨 **Original Email:**
**From:** {sender}
**Subject:** {subject}{metadata_line}

✍️ **AI-Generated Response:**

{truncated_draft}

---

Review the draft and choose an action:"""

    return message


def create_response_draft_keyboard(email_id: int) -> list[list[InlineKeyboardButton]]:
    """Create inline keyboard for response draft approval.

    Creates a Telegram inline keyboard with three action buttons:
    - Send: Send the response draft via Gmail
    - Edit: Allow user to edit the draft before sending
    - Reject: Discard the draft without sending

    Args:
        email_id: Email processing queue ID for workflow reconnection

    Returns:
        2D list of InlineKeyboardButton objects

    Callback Data Format:
        - send_response_{email_id}: User approves sending the draft
        - edit_response_{email_id}: User wants to edit the draft
        - reject_response_{email_id}: User rejects the draft

    Example:
        >>> keyboard = create_response_draft_keyboard(email_id=42)
        >>> # Renders as:
        >>> # [✉️ Send] [✏️ Edit]
        >>> #    [❌ Reject]
    """
    keyboard = [
        [
            InlineKeyboardButton("✉️ Send", callback_data=f"send_response_{email_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_response_{email_id}"),
        ],
        [
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_response_{email_id}"),
        ]
    ]
    return keyboard
