"""Telegram Markdown Utilities

Provides utilities for safely handling Telegram's MarkdownV2 format,
including escaping special characters and stripping markdown formatting.

Epic 1 - Story 1.1: Fix send_telegram Error Handling
"""

import re
from telegram.helpers import escape_markdown as telegram_escape_markdown


def escape_markdown(text: str, version: int = 2) -> str:
    """Escape special characters for Telegram MarkdownV2.

    Escapes all special characters that have meaning in Telegram's MarkdownV2:
    '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'

    Args:
        text: Text to escape
        version: Markdown version (1 or 2). Default is 2 (MarkdownV2)

    Returns:
        Escaped text safe for Telegram MarkdownV2 formatting

    Example:
        >>> escape_markdown("Project *Alpha* - Price: $100_000")
        'Project \\*Alpha\\* \\- Price: $100\\_000'
    """
    if not text:
        return ""

    # Use telegram-python-bot's built-in escaping
    return telegram_escape_markdown(text, version=version)


def strip_markdown(text: str) -> str:
    """Remove all markdown formatting from text.

    Removes common markdown formatting characters:
    - Bold: **text** or __text__
    - Italic: *text* or _text_
    - Code: `text` or ```text```
    - Links: [text](url)
    - Strikethrough: ~~text~~

    Args:
        text: Text with markdown formatting

    Returns:
        Plain text with formatting removed

    Example:
        >>> strip_markdown("**Bold** and *italic* text")
        'Bold and italic text'
    """
    if not text:
        return ""

    # Remove code blocks first (triple backticks)
    text = re.sub(r'```[^`]*```', '', text)

    # Remove inline code (single backticks)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove bold (**text** or __text__)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)

    # Remove italic (*text* or _text_)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove strikethrough (~~text~~)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)

    # Remove remaining special characters that might cause issues
    special_chars = ['>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(f'\\{char}', char)

    return text.strip()


def truncate_for_telegram(text: str, max_length: int = 4000) -> str:
    """Truncate text to fit Telegram's message length limit.

    Telegram has a 4096 character limit. This function truncates at max_length
    (default 4000) and adds "..." to indicate truncation.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation (default 4000)

    Returns:
        Truncated text with "..." if over limit

    Example:
        >>> long_text = "a" * 5000
        >>> truncated = truncate_for_telegram(long_text)
        >>> len(truncated)
        4003  # 4000 + "..."
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


def safe_format_telegram_message(text: str, use_markdown: bool = True) -> tuple[str, str]:
    """Safely format a message for Telegram with automatic fallback.

    Tries to escape markdown first. If that fails, returns plain text.

    Args:
        text: Message text to format
        use_markdown: Whether to attempt markdown formatting (default True)

    Returns:
        Tuple of (formatted_text, parse_mode)
        - formatted_text: Escaped text or plain text
        - parse_mode: 'MarkdownV2' or None

    Example:
        >>> safe_format_telegram_message("Hello *world*", use_markdown=True)
        ('Hello \\*world\\*', 'MarkdownV2')
        >>> safe_format_telegram_message("Hello *world*", use_markdown=False)
        ('Hello *world*', None)
    """
    if not text:
        return ("", None)

    # Truncate first
    text = truncate_for_telegram(text)

    if not use_markdown:
        return (text, None)

    try:
        # Attempt to escape for MarkdownV2
        escaped_text = escape_markdown(text, version=2)
        return (escaped_text, 'MarkdownV2')
    except Exception:
        # Fallback to plain text if escaping fails
        plain_text = strip_markdown(text)
        return (plain_text, None)
