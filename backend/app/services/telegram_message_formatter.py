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
    is_priority: bool = False
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

    Returns:
        Formatted message string with Markdown markup

    Example:
        >>> format_sorting_proposal_message(
        ...     sender="finanzamt@berlin.de",
        ...     subject="Tax Documents Required",
        ...     body_preview="Dear taxpayer, we require...",
        ...     proposed_folder="Government",
        ...     reasoning="Email from German tax office regarding documents.",
        ...     is_priority=True
        ... )
        '⚠️ **New Email Sorting Proposal**\\n\\n**From:** finanzamt@berlin.de...'
    """
    priority_icon = "⚠️ " if is_priority else ""

    # Truncate body preview to exactly 100 characters
    truncated_preview = body_preview[:100]
    if len(body_preview) > 100:
        truncated_preview += "..."

    message = f"""{priority_icon}**New Email Sorting Proposal**

**From:** {sender}
**Subject:** {subject}

**Preview:** {truncated_preview}

**AI Suggests:** Sort to "{proposed_folder}"
**Reasoning:** {reasoning}

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
