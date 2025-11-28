"""Email preprocessing utilities for embedding generation.

This module provides functions for preprocessing email content before
generating embeddings. It handles HTML stripping, text extraction from
various email formats, and token-based truncation.

Key Features:
- HTML tag removal while preserving text content
- Support for plain text and HTML email formats
- Token-based truncation (2048 token limit for Gemini embeddings)
- Robust handling of malformed HTML and encoding issues

Usage:
    from app.core.preprocessing import strip_html, extract_email_text, truncate_to_tokens

    # Strip HTML tags
    clean_text = strip_html("<p>Hello <b>world</b>!</p>")
    # Returns: "Hello world!"

    # Extract text from email body
    text = extract_email_text(email_body, content_type="text/html")

    # Truncate to token limit
    truncated = truncate_to_tokens(long_text, max_tokens=2048)
"""

import re
from typing import Optional

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)


def strip_html(html_content: str) -> str:
    """Remove HTML tags from content and return plain text.

    This function uses BeautifulSoup to parse HTML and extract text content,
    handling malformed HTML gracefully. It preserves text content while
    removing all HTML tags, scripts, and styles.

    Args:
        html_content: HTML string to process (may contain malformed HTML)

    Returns:
        Plain text with HTML tags removed, whitespace normalized

    Raises:
        ValueError: If html_content is None

    Examples:
        >>> strip_html("<p>Hello <b>world</b>!</p>")
        'Hello world!'

        >>> strip_html("<div>Text with <script>code</script> removed</div>")
        'Text with  removed'

        >>> strip_html("Plain text without tags")
        'Plain text without tags'

        >>> strip_html("<p>Malformed <b>HTML</p>")
        'Malformed HTML'
    """
    if html_content is None:
        raise ValueError("html_content cannot be None")

    if not html_content.strip():
        return ""

    try:
        # Parse HTML with BeautifulSoup (handles malformed HTML)
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Extract text
        text = soup.get_text()

        # Normalize whitespace: collapse multiple spaces/newlines into single space
        text = re.sub(r"\s+", " ", text).strip()

        logger.debug(
            "html_stripped",
            original_length=len(html_content),
            extracted_length=len(text),
        )

        return text

    except Exception as e:
        # Fallback: log error and return original content with tags removed via regex
        logger.warning(
            "html_strip_error_fallback",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Simple regex fallback (less robust but safer than crashing)
        text = re.sub(r"<[^>]+>", "", html_content)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def extract_email_text(email_body: str, content_type: str) -> str:
    """Extract plain text from email body based on content type.

    Handles both plain text (text/plain) and HTML (text/html) email formats.
    For HTML emails, strips tags and extracts text content. For plain text
    emails, returns content as-is with whitespace normalization.

    Args:
        email_body: Raw email body content
        content_type: MIME content type (e.g., "text/plain", "text/html")

    Returns:
        Extracted plain text with normalized whitespace

    Raises:
        ValueError: If email_body or content_type is None

    Examples:
        >>> extract_email_text("Hello world", "text/plain")
        'Hello world'

        >>> extract_email_text("<p>Hello <b>world</b></p>", "text/html")
        'Hello world'

        >>> extract_email_text("Text  with\\n\\nmultiple\\nlines", "text/plain")
        'Text with multiple lines'
    """
    if email_body is None:
        raise ValueError("email_body cannot be None")
    if content_type is None:
        raise ValueError("content_type cannot be None")

    if not email_body.strip():
        return ""

    # Normalize content type (handle charset parameters like "text/html; charset=utf-8")
    content_type_normalized = content_type.lower().split(";")[0].strip()

    try:
        if content_type_normalized == "text/html":
            # HTML email: strip tags and extract text
            text = strip_html(email_body)
        else:
            # Plain text email (or unknown type): normalize whitespace
            text = re.sub(r"\s+", " ", email_body).strip()

        logger.debug(
            "email_text_extracted",
            content_type=content_type_normalized,
            original_length=len(email_body),
            extracted_length=len(text),
        )

        return text

    except Exception as e:
        logger.error(
            "email_text_extraction_error",
            error=str(e),
            error_type=type(e).__name__,
            content_type=content_type,
        )
        # Fallback: return original with whitespace normalization
        return re.sub(r"\s+", " ", email_body).strip()


def truncate_to_tokens(text: str, max_tokens: int = 2048) -> str:
    """Truncate text to maximum token count for embedding API.

    This function uses a whitespace-based approximation for token counting,
    where tokens are approximately equal to words. This is suitable for
    most languages and provides a safe upper bound for Gemini's 2048 token limit.

    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens (default: 2048 for Gemini embeddings)

    Returns:
        Truncated text with at most max_tokens tokens

    Raises:
        ValueError: If text is None or max_tokens is not positive

    Examples:
        >>> truncate_to_tokens("one two three", max_tokens=2)
        'one two'

        >>> truncate_to_tokens("short text", max_tokens=2048)
        'short text'

        >>> text = " ".join([f"word{i}" for i in range(3000)])
        >>> result = truncate_to_tokens(text, max_tokens=2048)
        >>> len(result.split()) <= 2048
        True
    """
    if text is None:
        raise ValueError("text cannot be None")
    if max_tokens <= 0:
        raise ValueError(f"max_tokens must be positive, got {max_tokens}")

    if not text.strip():
        return ""

    # Split by whitespace to approximate tokens
    tokens = text.split()

    if len(tokens) <= max_tokens:
        # No truncation needed
        logger.debug(
            "truncate_to_tokens_no_op",
            token_count=len(tokens),
            max_tokens=max_tokens,
        )
        return text

    # Truncate to max_tokens
    truncated_tokens = tokens[:max_tokens]
    truncated_text = " ".join(truncated_tokens)

    logger.info(
        "text_truncated",
        original_tokens=len(tokens),
        truncated_tokens=len(truncated_tokens),
        max_tokens=max_tokens,
        truncation_ratio=len(truncated_tokens) / len(tokens),
    )

    return truncated_text
