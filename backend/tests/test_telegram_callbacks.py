"""Unit tests for Telegram callback handlers (Story 2.7).

Tests cover:
- Callback data parsing
- User ownership validation
- Approve/reject/change folder handlers
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session, select

from app.api.telegram_handlers import (
    parse_callback_data,
    validate_user_owns_email,
    handle_callback_query,
)
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.models.workflow_mapping import WorkflowMapping


class TestCallbackDataParsing:
    """Test parse_callback_data function (AC #1, #7)."""

    def test_approve_callback_format(self):
        """Test parsing approve_{email_id} callback data."""
        action, email_id, folder_id = parse_callback_data("approve_123")

        assert action == "approve"
        assert email_id == 123
        assert folder_id is None

    def test_reject_callback_format(self):
        """Test parsing reject_{email_id} callback data."""
        action, email_id, folder_id = parse_callback_data("reject_456")

        assert action == "reject"
        assert email_id == 456
        assert folder_id is None

    def test_change_folder_callback_format(self):
        """Test parsing change_{email_id} callback data."""
        action, email_id, folder_id = parse_callback_data("change_789")

        assert action == "change"
        assert email_id == 789
        assert folder_id is None

    def test_folder_selection_callback_format(self):
        """Test parsing folder_{folder_id}_{email_id} callback data."""
        action, email_id, folder_id = parse_callback_data("folder_5_123")

        assert action == "folder"
        assert email_id == 123
        assert folder_id == 5

    def test_malformed_callback_data_too_short(self):
        """Test error handling for malformed callback data (too few parts)."""
        with pytest.raises(ValueError, match="Invalid callback data format"):
            parse_callback_data("approve")

    def test_malformed_callback_data_invalid_email_id(self):
        """Test error handling for non-numeric email_id."""
        with pytest.raises(ValueError, match="Invalid email_id in callback"):
            parse_callback_data("approve_abc")

    def test_malformed_folder_callback_format(self):
        """Test error handling for malformed folder callback."""
        with pytest.raises(ValueError, match="Invalid folder callback format"):
            parse_callback_data("folder_5")  # Missing email_id

    def test_unknown_action(self):
        """Test error handling for unknown action."""
        with pytest.raises(ValueError, match="Unknown action"):
            parse_callback_data("unknown_123")


class TestUserOwnershipValidation:
    """Test validate_user_owns_email function (AC #8)."""

    @pytest.mark.asyncio
    async def test_valid_ownership(self, db_session, test_user, test_email):
        """Test validation passes when user owns the email."""
        # Setup: test_user owns test_email (from fixtures)
        telegram_user_id = int(test_user.telegram_id)

        result = await validate_user_owns_email(telegram_user_id, test_email.id, db_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_user_not_found(self, db_session):
        """Test validation fails when telegram user not in database."""
        result = await validate_user_owns_email(telegram_user_id=999999, email_id=1, db=db_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_email_not_found(self, db_session, test_user):
        """Test validation fails when email not in database."""
        telegram_user_id = int(test_user.telegram_id)

        result = await validate_user_owns_email(telegram_user_id, email_id=999999, db=db_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_ownership_mismatch(self, db_session, test_user, test_user_2, test_email):
        """Test validation fails when user doesn't own the email."""
        # test_email belongs to test_user, but we check with test_user_2
        telegram_user_id = int(test_user_2.telegram_id)

        result = await validate_user_owns_email(telegram_user_id, test_email.id, db_session)

        assert result is False


class TestCallbackQueryHandler:
    """Test handle_callback_query routing function."""

    @pytest.mark.asyncio
    async def test_callback_query_routing_to_approve(self, mock_callback_query, db_session, test_email, test_user):
        """Test callback query routes to approve handler."""
        # Setup
        mock_callback_query.callback_query.data = f"approve_{test_email.id}"
        mock_callback_query.callback_query.from_user.id = int(test_user.telegram_id)

        with patch("app.api.telegram_handlers.handle_approve", new_callable=AsyncMock) as mock_approve:
            await handle_callback_query(mock_callback_query, None)

            # Verify approve handler was called
            mock_approve.assert_called_once()
            args = mock_approve.call_args[0]
            assert args[0] == mock_callback_query.callback_query
            assert args[1] == test_email.id

    @pytest.mark.asyncio
    async def test_callback_query_unauthorized(self, mock_callback_query, db_session, test_email):
        """Test callback query rejects unauthorized user (AC #8)."""
        # Setup: Use a telegram_id that doesn't exist
        mock_callback_query.callback_query.data = f"approve_{test_email.id}"
        mock_callback_query.callback_query.from_user.id = 999999

        await handle_callback_query(mock_callback_query, None)

        # Verify unauthorized message sent
        mock_callback_query.callback_query.answer.assert_called_once_with("❌ Unauthorized", show_alert=True)

    @pytest.mark.asyncio
    async def test_callback_query_malformed_data(self, mock_callback_query):
        """Test callback query handles malformed data gracefully."""
        mock_callback_query.callback_query.data = "malformed"

        await handle_callback_query(mock_callback_query, None)

        # Verify error message sent
        mock_callback_query.callback_query.answer.assert_called_once_with("❌ Invalid button data", show_alert=True)


# Pytest Fixtures
@pytest.fixture
def mock_callback_query():
    """Create mock Telegram Update object with CallbackQuery."""
    # Create the Update mock (this is what handle_callback_query receives)
    update = MagicMock()

    # Create the callback_query mock
    callback_query = MagicMock()
    callback_query.answer = AsyncMock()
    callback_query.from_user = MagicMock()
    callback_query.from_user.id = 123456789
    callback_query.data = "approve_1"

    # Attach callback_query to update
    update.callback_query = callback_query

    return update
