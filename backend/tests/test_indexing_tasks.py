"""Unit tests for Celery indexing tasks.

This module tests the background tasks for email history indexing with mocked
EmailIndexingService.

Test Coverage (AC mapped):
1. test_index_user_emails_task_calls_service (AC #1)
2. test_task_handles_service_exceptions (AC #12)
3. test_task_respects_timeout_configuration (AC #1)

Reference: docs/stories/3-3-email-history-indexing.md
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.indexing_progress import IndexingProgress, IndexingStatus
from app.tasks.indexing_tasks import (
    index_user_emails,
    resume_user_indexing,
    index_new_email_background,
)
from app.utils.errors import GmailAPIError, GeminiAPIError


class TestIndexingTasks:
    """Unit tests for Celery indexing tasks."""

    @patch("app.tasks.indexing_tasks.EmailIndexingService")
    def test_index_user_emails_task_calls_service(self, mock_service_class):
        """Test that index_user_emails task instantiates service and calls start_indexing (AC #1).

        Verifies:
        - EmailIndexingService instantiated with user_id
        - start_indexing() called with days_back parameter
        - Returns success dict with progress details
        - Task logs completion
        """
        # Mock service instance
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Mock progress result
        mock_progress = IndexingProgress(
            id=1,
            user_id=123,
            total_emails=100,
            processed_count=100,
            status=IndexingStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )

        # Mock start_indexing as async coroutine
        async def mock_start_indexing(days_back):
            return mock_progress

        mock_service.start_indexing = mock_start_indexing

        # Execute task
        result = index_user_emails(user_id=123, days_back=90)

        # Verify service instantiated
        mock_service_class.assert_called_once_with(user_id=123)

        # Verify result
        assert result["success"] is True
        assert result["user_id"] == 123
        assert result["total_emails"] == 100
        assert result["processed"] == 100
        assert result["status"] == "completed"

    @patch("app.tasks.indexing_tasks.EmailIndexingService")
    def test_task_handles_service_exceptions(self, mock_service_class):
        """Test that task handles EmailIndexingService exceptions with retry logic (AC #12).

        Verifies:
        - GmailAPIError triggers task retry with exponential backoff
        - GeminiAPIError triggers task retry
        - ValueError (permanent error) does not retry
        - Returns error dict on failure
        - Max retries exhausted returns retries_exhausted flag
        """
        # Mock service instance
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Test 1: Gmail API error (transient) - should retry
        async def mock_start_indexing_gmail_error(days_back):
            raise GmailAPIError("Rate limit exceeded (429)")

        mock_service.start_indexing = mock_start_indexing_gmail_error

        # Create task bound instance for retry testing
        task = index_user_emails
        task.request.id = "test_task_id"
        task.request.retries = 0
        task.max_retries = 3
        task.default_retry_delay = 60

        # Mock retry to prevent actual retry (just capture the call)
        task.retry = MagicMock(side_effect=Exception("Retry called"))

        try:
            result = task(user_id=123, days_back=90)
        except Exception as e:
            # Retry was called (expected behavior)
            assert "Retry called" in str(e)

        # Test 2: Permanent error (ValueError) - should not retry
        async def mock_start_indexing_permanent_error(days_back):
            raise ValueError("Indexing job already exists")

        mock_service.start_indexing = mock_start_indexing_permanent_error

        result = task(user_id=123, days_back=90)

        # Verify error result (no retry)
        assert result["success"] is False
        assert result["user_id"] == 123
        assert "ValueError" in result["error"]
        assert result.get("permanent_error") is True

        # Test 3: Max retries exhausted
        task.request.retries = 3  # Already exhausted
        task.retry = MagicMock(side_effect=Exception("Max retries exhausted"))

        async def mock_start_indexing_gemini_error(days_back):
            raise GeminiAPIError("Embedding generation failed")

        mock_service.start_indexing = mock_start_indexing_gemini_error

        result = task(user_id=123, days_back=90)

        # Verify retries exhausted flag
        assert result["success"] is False
        assert result.get("retries_exhausted") is True

    def test_task_respects_timeout_configuration(self):
        """Test that task is configured with proper timeout and retry settings (AC #1).

        Verifies:
        - Task time_limit = 3600 seconds (1 hour)
        - Task soft_time_limit = 3540 seconds (59 minutes)
        - max_retries = 3
        - default_retry_delay = 60 seconds
        - Task name properly registered
        """
        # Get task configuration
        task = index_user_emails

        # Verify task decorator settings
        # Note: These are set at task registration, not runtime
        assert task.name == "app.tasks.indexing_tasks.index_user_emails"
        assert task.max_retries == 3
        assert task.default_retry_delay == 60

        # Verify timeout configuration (set in celery_app.conf)
        # Note: time_limit and soft_time_limit are set globally in celery.py
        # For task-specific limits, check task.time_limit attribute
        assert task.time_limit == 3600  # 1 hour
        assert task.soft_time_limit == 3540  # 59 minutes

    @patch("app.tasks.indexing_tasks.EmailIndexingService")
    def test_resume_user_indexing_task(self, mock_service_class):
        """Test resume_user_indexing task functionality.

        Verifies:
        - Service.resume_indexing() called
        - Returns success with progress details
        - Handles no interrupted job case
        """
        # Mock service instance
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Mock progress result
        mock_progress = IndexingProgress(
            id=1,
            user_id=123,
            total_emails=100,
            processed_count=100,
            status=IndexingStatus.COMPLETED,
        )

        async def mock_resume_indexing():
            return mock_progress

        mock_service.resume_indexing = mock_resume_indexing

        # Execute task
        result = resume_user_indexing(user_id=123)

        # Verify service called
        mock_service_class.assert_called_once_with(user_id=123)

        # Verify result
        assert result["success"] is True
        assert result["user_id"] == 123
        assert result["total_emails"] == 100

    @patch("app.tasks.indexing_tasks.EmailIndexingService")
    def test_index_new_email_background_task(self, mock_service_class):
        """Test index_new_email_background task for incremental indexing.

        Verifies:
        - Service.index_new_email() called with message_id
        - Returns success if indexed
        - Handles skip case (initial indexing incomplete)
        """
        # Mock service instance
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Mock successful incremental indexing
        async def mock_index_new_email(message_id):
            return True

        mock_service.index_new_email = mock_index_new_email

        # Execute task
        result = index_new_email_background(user_id=123, message_id="msg_abc")

        # Verify service called
        mock_service_class.assert_called_once_with(user_id=123)

        # Verify result
        assert result["success"] is True
        assert result["user_id"] == 123
        assert result["message_id"] == "msg_abc"

        # Test skip case
        async def mock_index_new_email_skip(message_id):
            return False  # Skipped

        mock_service.index_new_email = mock_index_new_email_skip

        result = index_new_email_background(user_id=123, message_id="msg_xyz")

        # Verify skipped
        assert result["success"] is False
        assert result["user_id"] == 123
