"""Unit tests for Telegram message formatting service."""

import pytest
from telegram import InlineKeyboardButton

from app.services.telegram_message_formatter import (
    format_sorting_proposal_message,
    create_inline_keyboard,
)


class TestFormatSortingProposalMessage:
    """Test cases for format_sorting_proposal_message function."""

    def test_format_regular_email(self):
        """Test formatting a regular (non-priority) email."""
        result = format_sorting_proposal_message(
            sender="john@example.com",
            subject="Project Update",
            body_preview="Here is the latest update on our project progress...",
            proposed_folder="Work",
            reasoning="Email from colleague regarding project status",
            is_priority=False,
        )

        assert "**New Email Sorting Proposal**" in result
        assert "**From:** john@example.com" in result
        assert "**Subject:** Project Update" in result
        assert "**Preview:** Here is the latest update on our project progress..." in result
        assert '**AI Suggests:** Sort to "Work"' in result
        assert "**Reasoning:** Email from colleague regarding project status" in result
        assert "What would you like to do?" in result
        # Should NOT have priority icon
        assert "⚠️" not in result

    def test_format_priority_email(self):
        """Test formatting a priority email (has ⚠️ icon)."""
        result = format_sorting_proposal_message(
            sender="boss@company.com",
            subject="URGENT: Client Meeting Tomorrow",
            body_preview="We have an urgent client meeting scheduled...",
            proposed_folder="Important",
            reasoning="Urgent meeting invitation from manager",
            is_priority=True,
        )

        assert "⚠️ **New Email Sorting Proposal**" in result
        assert "**From:** boss@company.com" in result
        assert "**Subject:** URGENT: Client Meeting Tomorrow" in result
        assert '**AI Suggests:** Sort to "Important"' in result

    def test_body_preview_truncation_at_100_chars(self):
        """Test that body preview is truncated to exactly 100 characters."""
        long_body = "a" * 150  # 150 characters

        result = format_sorting_proposal_message(
            sender="test@example.com",
            subject="Test",
            body_preview=long_body,
            proposed_folder="Test",
            reasoning="Test email",
            is_priority=False,
        )

        # Should be truncated to 100 chars + "..."
        assert f"**Preview:** {'a' * 100}..." in result
        # Verify no more than 100 chars (not counting "...")
        preview_line = [line for line in result.split("\n") if "**Preview:**" in line][0]
        # Remove "**Preview:** " (14 chars) and "..." (3 chars)
        preview_content = preview_line.replace("**Preview:** ", "").replace("...", "")
        assert len(preview_content) == 100

    def test_body_preview_no_truncation_under_100_chars(self):
        """Test that body preview under 100 chars is not truncated."""
        short_body = "This is a short email."

        result = format_sorting_proposal_message(
            sender="test@example.com",
            subject="Test",
            body_preview=short_body,
            proposed_folder="Test",
            reasoning="Test email",
            is_priority=False,
        )

        assert f"**Preview:** {short_body}" in result
        # Should NOT have "..."
        preview_line = [line for line in result.split("\n") if "**Preview:**" in line][0]
        assert not preview_line.endswith("...")

    def test_markdown_escaping_special_chars(self):
        """Test that special characters in email content are preserved."""
        result = format_sorting_proposal_message(
            sender="test@example.com",
            subject="Re: Question about $1000 payment & invoice #123",
            body_preview="Payment details: $1000 & invoice #123...",
            proposed_folder="Finance",
            reasoning="Financial email with special characters",
            is_priority=False,
        )

        # Special characters should be preserved in the message
        assert "Re: Question about $1000 payment & invoice #123" in result
        assert "Payment details: $1000 & invoice #123..." in result

    def test_empty_body_preview(self):
        """Test handling of empty body preview."""
        result = format_sorting_proposal_message(
            sender="test@example.com",
            subject="Empty Body Test",
            body_preview="",
            proposed_folder="Test",
            reasoning="Email with no body",
            is_priority=False,
        )

        assert "**Preview:** " in result
        assert "**From:** test@example.com" in result

    def test_message_structure(self):
        """Test that message has correct structure and sections."""
        result = format_sorting_proposal_message(
            sender="test@example.com",
            subject="Test Subject",
            body_preview="Test body",
            proposed_folder="Test Folder",
            reasoning="Test reasoning",
            is_priority=False,
        )

        lines = result.split("\n")
        # Verify key sections are present in order
        assert any("**New Email Sorting Proposal**" in line for line in lines)
        assert any("**From:**" in line for line in lines)
        assert any("**Subject:**" in line for line in lines)
        assert any("**Preview:**" in line for line in lines)
        assert any("**AI Suggests:**" in line for line in lines)
        assert any("**Reasoning:**" in line for line in lines)
        assert any("What would you like to do?" in line for line in lines)


class TestCreateInlineKeyboard:
    """Test cases for create_inline_keyboard function."""

    def test_keyboard_structure(self):
        """Test that keyboard has correct structure (3 buttons in 2 rows)."""
        keyboard = create_inline_keyboard(email_id=42)

        # Should return 2D list of buttons
        assert isinstance(keyboard, list)
        assert len(keyboard) == 2  # 2 rows
        assert len(keyboard[0]) == 2  # First row: Approve, Change Folder
        assert len(keyboard[1]) == 1  # Second row: Reject

    def test_button_labels(self):
        """Test that buttons have correct labels."""
        keyboard = create_inline_keyboard(email_id=42)

        # First row buttons
        assert keyboard[0][0].text == "✅ Approve"
        assert keyboard[0][1].text == "📁 Change Folder"
        # Second row button
        assert keyboard[1][0].text == "❌ Reject"

    def test_callback_data_format(self):
        """Test that callback_data follows format: {action}_{email_id}."""
        email_id = 123
        keyboard = create_inline_keyboard(email_id=email_id)

        # First row callbacks
        assert keyboard[0][0].callback_data == f"approve_{email_id}"
        assert keyboard[0][1].callback_data == f"change_{email_id}"
        # Second row callback
        assert keyboard[1][0].callback_data == f"reject_{email_id}"

    def test_callback_data_with_different_email_ids(self):
        """Test that callback_data changes with different email IDs."""
        keyboard1 = create_inline_keyboard(email_id=100)
        keyboard2 = create_inline_keyboard(email_id=200)

        assert keyboard1[0][0].callback_data == "approve_100"
        assert keyboard2[0][0].callback_data == "approve_200"

    def test_button_types(self):
        """Test that buttons are InlineKeyboardButton instances."""
        keyboard = create_inline_keyboard(email_id=42)

        for row in keyboard:
            for button in row:
                assert isinstance(button, InlineKeyboardButton)
