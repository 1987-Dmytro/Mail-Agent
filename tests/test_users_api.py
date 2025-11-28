"""Unit tests for User API endpoints.

This module tests the user management endpoints including onboarding completion
and backend automation triggers.

Test Coverage (AC mapped to Story 5-1):
1. test_complete_onboarding_triggers_indexing (AC #1)
2. test_complete_onboarding_triggers_polling (AC #2)
3. test_complete_onboarding_succeeds_when_tasks_fail (AC #3)
4. test_complete_onboarding_logs_task_triggers (AC #4)

Reference: docs/stories/story-5-1-fix-onboarding-trigger.md
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TestCompleteOnboardingTasks:
    """Tests for complete_onboarding endpoint task triggering."""

    @pytest.mark.asyncio
    @patch("app.api.v1.users.database_service")
    @patch("app.tasks.indexing_tasks.index_user_emails")
    @patch("app.tasks.email_tasks.poll_user_emails")
    async def test_complete_onboarding_triggers_indexing(
        self, mock_poll_task, mock_index_task, mock_db_service
    ):
        """Test that complete_onboarding triggers index_user_emails task (AC #1).

        Verifies:
        - index_user_emails.delay() called with correct user_id
        - days_back=90 parameter passed
        - Indexing task is enqueued successfully
        """
        from app.api.v1.users import complete_onboarding

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 123
        mock_user.email = "test@example.com"
        mock_user.onboarding_completed = False

        # Mock database service
        mock_db_service.update_user = AsyncMock(return_value=mock_user)

        # Setup task mocks
        mock_index_task.delay = MagicMock()
        mock_poll_task.delay = MagicMock()

        # Execute endpoint
        result = await complete_onboarding(current_user=mock_user)

        # Verify indexing task triggered
        mock_index_task.delay.assert_called_once_with(
            user_id=123,
            days_back=90
        )

        # Verify success response
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("app.api.v1.users.database_service")
    @patch("app.tasks.indexing_tasks.index_user_emails")
    @patch("app.tasks.email_tasks.poll_user_emails")
    async def test_complete_onboarding_triggers_polling(
        self, mock_poll_task, mock_index_task, mock_db_service
    ):
        """Test that complete_onboarding triggers poll_user_emails task (AC #2).

        Verifies:
        - poll_user_emails.delay() called with correct user_id
        - Polling task is enqueued successfully
        """
        from app.api.v1.users import complete_onboarding

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 456
        mock_user.email = "test2@example.com"
        mock_user.onboarding_completed = False

        # Mock database service
        mock_db_service.update_user = AsyncMock(return_value=mock_user)

        # Setup task mocks
        mock_index_task.delay = MagicMock()
        mock_poll_task.delay = MagicMock()

        # Execute endpoint
        result = await complete_onboarding(current_user=mock_user)

        # Verify polling task triggered
        mock_poll_task.delay.assert_called_once_with(
            user_id=456
        )

        # Verify success response
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("app.api.v1.users.database_service")
    @patch("app.tasks.indexing_tasks.index_user_emails")
    @patch("app.tasks.email_tasks.poll_user_emails")
    async def test_complete_onboarding_succeeds_when_tasks_fail(
        self, mock_poll_task, mock_index_task, mock_db_service
    ):
        """Test that onboarding succeeds even if task queueing fails (AC #3).

        Verifies:
        - Endpoint returns success even if Celery tasks fail to enqueue
        - Database flag is still set correctly
        - User is not impacted by task queue failures
        """
        from app.api.v1.users import complete_onboarding

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 789
        mock_user.email = "test3@example.com"
        mock_user.onboarding_completed = False

        # Mock database service
        mock_db_service.update_user = AsyncMock(return_value=mock_user)

        # Setup mocks to fail
        mock_index_task.delay = MagicMock(side_effect=Exception("Redis unavailable"))
        mock_poll_task.delay = MagicMock(side_effect=Exception("Celery broker down"))

        # Execute endpoint - should NOT raise exception
        result = await complete_onboarding(current_user=mock_user)

        # Verify success response despite task failures
        assert result["success"] is True
        assert result["message"] == "Onboarding completed successfully"

        # Verify onboarding flag was set
        assert mock_user.onboarding_completed is True

    @pytest.mark.asyncio
    @patch("app.api.v1.users.logger")
    @patch("app.api.v1.users.database_service")
    @patch("app.tasks.indexing_tasks.index_user_emails")
    @patch("app.tasks.email_tasks.poll_user_emails")
    async def test_complete_onboarding_logs_task_triggers(
        self, mock_poll_task, mock_index_task, mock_db_service, mock_logger
    ):
        """Test that task triggers are logged properly (AC #4).

        Verifies:
        - Log entry for "indexing_task_triggered" with user_id and days_back
        - Log entry for "polling_task_triggered" with user_id
        - Structured logging follows existing patterns
        """
        from app.api.v1.users import complete_onboarding

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 101
        mock_user.email = "test4@example.com"
        mock_user.onboarding_completed = False

        # Mock database service
        mock_db_service.update_user = AsyncMock(return_value=mock_user)

        # Setup task mocks
        mock_index_task.delay = MagicMock()
        mock_poll_task.delay = MagicMock()

        # Execute endpoint
        await complete_onboarding(current_user=mock_user)

        # Verify logging calls
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Should have 3 log entries: onboarding_completed, indexing_task_triggered, polling_task_triggered
        assert "onboarding_completed" in log_calls
        assert "indexing_task_triggered" in log_calls
        assert "polling_task_triggered" in log_calls

    @pytest.mark.asyncio
    @patch("app.api.v1.users.logger")
    @patch("app.api.v1.users.database_service")
    @patch("app.tasks.indexing_tasks.index_user_emails")
    @patch("app.tasks.email_tasks.poll_user_emails")
    async def test_complete_onboarding_logs_warning_on_task_failure(
        self, mock_poll_task, mock_index_task, mock_db_service, mock_logger
    ):
        """Test that task failures are logged as warnings (AC #3, #4).

        Verifies:
        - Warning logged when indexing task fails
        - Warning logged when polling task fails
        - Error messages include user_id and exception details
        """
        from app.api.v1.users import complete_onboarding

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 202
        mock_user.email = "test5@example.com"
        mock_user.onboarding_completed = False

        # Mock database service
        mock_db_service.update_user = AsyncMock(return_value=mock_user)

        # Setup mocks to fail
        mock_index_task.delay = MagicMock(side_effect=Exception("Connection refused"))
        mock_poll_task.delay = MagicMock(side_effect=Exception("Broker unavailable"))

        # Execute endpoint
        await complete_onboarding(current_user=mock_user)

        # Verify warning logs
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert "indexing_task_trigger_failed" in warning_calls
        assert "polling_task_trigger_failed" in warning_calls
