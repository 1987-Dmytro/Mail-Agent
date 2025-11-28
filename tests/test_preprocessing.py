"""Unit tests for email preprocessing module.

Tests cover AC #3: Email content preprocessing implemented (HTML stripping,
text extraction, truncation to 2048 tokens max).

Test Functions:
1. test_strip_html_removes_tags() - Verify HTML tag removal (AC #3)
2. test_extract_email_text_handles_plain_and_html() - Verify email text extraction (AC #3)
3. test_truncate_to_tokens_respects_limit() - Verify token truncation (AC #3)
"""

import pytest

from app.core.preprocessing import (
    strip_html,
    extract_email_text,
    truncate_to_tokens,
)


class TestStripHTML:
    """Test suite for strip_html() function.

    Acceptance Criteria: AC #3 - HTML stripping, text preservation
    """

    def test_strip_html_removes_tags(self):
        """Verify strip_html() removes HTML tags and preserves text (AC #3).

        Test cases:
        - Simple tags (<p>, <b>, <i>)
        - Nested tags
        - Malformed HTML (unclosed tags)
        - Script/style removal
        - Empty input
        """
        # Simple tags
        assert strip_html("<p>Hello <b>world</b>!</p>") == "Hello world!"
        assert strip_html("<div>Text</div>") == "Text"

        # Nested tags
        assert strip_html("<div><p>Nested <b><i>tags</i></b></p></div>") == "Nested tags"

        # Malformed HTML (BeautifulSoup handles gracefully)
        assert strip_html("<p>Unclosed <b>tag") == "Unclosed tag"
        assert strip_html("<div>Overlap <b>ping</div> tags</b>") == "Overlap ping tags"

        # Script and style removal
        assert strip_html("<p>Text</p><script>alert('x')</script>") == "Text"
        assert strip_html("<style>body{}</style><p>Content</p>") == "Content"

        # Empty input
        assert strip_html("") == ""
        assert strip_html("   ") == ""

        # Plain text (no tags)
        assert strip_html("Plain text without tags") == "Plain text without tags"

        # Whitespace normalization
        assert strip_html("<p>Multiple    spaces</p>") == "Multiple spaces"
        assert strip_html("<p>Line\nbreaks\n\nhere</p>") == "Line breaks here"

    def test_strip_html_handles_encoding_issues(self):
        """Verify strip_html() handles special characters and encoding (AC #3)."""
        # Unicode characters
        assert strip_html("<p>Привет мир</p>") == "Привет мир"
        assert strip_html("<p>Hallo Welt 🌍</p>") == "Hallo Welt 🌍"

        # HTML entities (BeautifulSoup decodes them)
        assert strip_html("<p>A &amp; B</p>") == "A & B"
        assert strip_html("<p>2 &lt; 3</p>") == "2 < 3"

    def test_strip_html_raises_on_none(self):
        """Verify strip_html() raises ValueError on None input (AC #3)."""
        with pytest.raises(ValueError, match="cannot be None"):
            strip_html(None)


class TestExtractEmailText:
    """Test suite for extract_email_text() function.

    Acceptance Criteria: AC #3 - Email text extraction from plain/HTML formats
    """

    def test_extract_email_text_handles_plain_and_html(self):
        """Verify extract_email_text() handles plain and HTML emails (AC #3).

        Test cases:
        - text/plain content type
        - text/html content type
        - Content type with charset parameter
        - Empty email body
        """
        # Plain text email
        plain_body = "Hello world\nThis is a plain text email."
        assert extract_email_text(plain_body, "text/plain") == "Hello world This is a plain text email."

        # HTML email
        html_body = "<html><body><p>Hello <b>world</b></p></body></html>"
        assert extract_email_text(html_body, "text/html") == "Hello world"

        # Content type with charset
        assert extract_email_text(html_body, "text/html; charset=utf-8") == "Hello world"
        assert extract_email_text(plain_body, "text/plain; charset=iso-8859-1") == "Hello world This is a plain text email."

        # Mixed case content type
        assert extract_email_text(html_body, "TEXT/HTML") == "Hello world"

        # Empty email body
        assert extract_email_text("", "text/plain") == ""
        assert extract_email_text("   ", "text/html") == ""

    def test_extract_email_text_handles_whitespace(self):
        """Verify whitespace normalization in email text extraction (AC #3)."""
        # Multiple spaces
        assert extract_email_text("Text  with   spaces", "text/plain") == "Text with spaces"

        # Multiple newlines
        assert extract_email_text("Line1\n\n\nLine2", "text/plain") == "Line1 Line2"

        # Mixed whitespace
        assert extract_email_text("Tab\there\nand  spaces", "text/plain") == "Tab here and spaces"

    def test_extract_email_text_raises_on_none(self):
        """Verify extract_email_text() raises ValueError on None inputs (AC #3)."""
        with pytest.raises(ValueError, match="email_body cannot be None"):
            extract_email_text(None, "text/plain")

        with pytest.raises(ValueError, match="content_type cannot be None"):
            extract_email_text("body", None)


class TestTruncateToTokens:
    """Test suite for truncate_to_tokens() function.

    Acceptance Criteria: AC #3 - Truncation to 2048 tokens max
    """

    def test_truncate_to_tokens_respects_limit(self):
        """Verify truncate_to_tokens() respects token limit (AC #3).

        Test cases:
        - Short text (no truncation)
        - Long text (truncation needed)
        - Edge case at exactly max_tokens
        - Custom max_tokens value
        """
        # Short text - no truncation
        short_text = "one two three four five"
        assert truncate_to_tokens(short_text, max_tokens=2048) == short_text
        assert truncate_to_tokens(short_text, max_tokens=10) == short_text

        # Long text - truncation needed
        long_text = " ".join([f"word{i}" for i in range(3000)])
        truncated = truncate_to_tokens(long_text, max_tokens=2048)
        assert len(truncated.split()) == 2048
        assert truncated.startswith("word0 word1")

        # Edge case: exactly max_tokens
        exact_text = " ".join([f"w{i}" for i in range(2048)])
        assert truncate_to_tokens(exact_text, max_tokens=2048) == exact_text

        # Custom max_tokens
        text = "one two three four five"
        assert truncate_to_tokens(text, max_tokens=2) == "one two"
        assert truncate_to_tokens(text, max_tokens=3) == "one two three"

    def test_truncate_to_tokens_handles_edge_cases(self):
        """Verify truncate_to_tokens() handles edge cases (AC #3)."""
        # Empty text
        assert truncate_to_tokens("", max_tokens=2048) == ""
        assert truncate_to_tokens("   ", max_tokens=2048) == ""

        # Single word
        assert truncate_to_tokens("word", max_tokens=2048) == "word"
        assert truncate_to_tokens("word", max_tokens=1) == "word"

        # Exactly at boundary
        text = " ".join(["x"] * 100)
        assert len(truncate_to_tokens(text, max_tokens=100).split()) == 100

    def test_truncate_to_tokens_raises_on_invalid_input(self):
        """Verify truncate_to_tokens() validates inputs (AC #3)."""
        # None text
        with pytest.raises(ValueError, match="text cannot be None"):
            truncate_to_tokens(None, max_tokens=2048)

        # Non-positive max_tokens
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            truncate_to_tokens("text", max_tokens=0)

        with pytest.raises(ValueError, match="max_tokens must be positive"):
            truncate_to_tokens("text", max_tokens=-10)


# Pytest fixtures for sample data
@pytest.fixture
def sample_html_email():
    """Sample HTML email for testing."""
    return """
    <html>
    <head><title>Test Email</title></head>
    <body>
        <p>Dear User,</p>
        <p>This is a <b>test</b> email with <i>formatting</i>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <script>alert('Should be removed')</script>
    </body>
    </html>
    """


@pytest.fixture
def sample_plain_email():
    """Sample plain text email for testing."""
    return """Dear User,

This is a plain text email.

Best regards,
System"""


# Integration-style tests using fixtures
class TestPreprocessingIntegration:
    """Integration tests for complete preprocessing pipeline."""

    def test_complete_html_email_pipeline(self, sample_html_email):
        """Test complete preprocessing pipeline for HTML email (AC #3)."""
        # Extract text from HTML email
        text = extract_email_text(sample_html_email, "text/html")

        # Verify HTML tags removed
        assert "<" not in text
        assert ">" not in text
        assert "Dear User" in text
        assert "test" in text
        assert "formatting" in text
        assert "Item 1" in text

        # Truncate to small limit
        truncated = truncate_to_tokens(text, max_tokens=5)
        assert len(truncated.split()) == 5

    def test_complete_plain_email_pipeline(self, sample_plain_email):
        """Test complete preprocessing pipeline for plain text email (AC #3)."""
        # Extract text from plain email
        text = extract_email_text(sample_plain_email, "text/plain")

        # Verify whitespace normalized
        assert "Dear User" in text
        assert "plain text email" in text
        assert "\n\n" not in text  # Multiple newlines collapsed

        # Truncate
        truncated = truncate_to_tokens(text, max_tokens=10)
        assert len(truncated.split()) <= 10
