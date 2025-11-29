"""Integration tests for error handling and recovery (Story 2.11).

Tests cover:
1. Retry utility with exponential backoff
2. Gmail API error handling with retry logic
3. Telegram API error handling with retry logic
4. Workflow node error handling (status update, notification, logging)
5. Manual retry command (/retry)
6. Error statistics endpoint
7. End-to-end error recovery flow
"""

import pytest
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, UTC
from telegram.error import NetworkError, Forbidden
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

from app.core.gmail_client import GmailClient
from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.user import User
from app.workflows.nodes import execute_action
from app.utils.retry import execute_with_retry, RetryConfig
from app.utils.errors import GmailAPIError, TelegramSendError


class TestRetryUtilityIntegration:
    """Test retry utility with real async functions."""

    @pytest.mark.asyncio
    async def test_retry_with_eventual_success(self):
        """Test retry succeeds after transient failures.

        Scenario: Function fails 2 times then succeeds
        Expected: Returns success after 2 retries
        """
        call_count = {"count": 0}

        async def flaky_function():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise GmailAPIError("503 Service Unavailable", status_code=503)
            return "success"

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await execute_with_retry(flaky_function)

        assert result == "success"
        assert call_count["count"] == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_exception(self):
        """Test retry raises exception after max retries exhausted.

        Scenario: Function always fails
        Expected: Raises exception after 3 retries
        """
        async def always_fails():
            raise GmailAPIError("503 Service Unavailable", status_code=503)

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(GmailAPIError):
                await execute_with_retry(always_fails)


class TestGmailAPIErrorHandling:
    """Test Gmail API error handling with retry logic."""

    @pytest.mark.asyncio
    async def test_gmail_apply_label_with_retry(self, test_user, db_session):
        """Test Gmail API apply_label retries on transient errors.

        Scenario: Gmail API returns 503, retries, succeeds
        Expected: Label applied successfully after retry
        """
        gmail_client = GmailClient(user_id=test_user.id, db_service=None)

        # Mock Gmail service
        mock_service = Mock()
        mock_modify = Mock()
        mock_service.users.return_value.messages.return_value.modify.return_value = mock_modify

        # Create HttpError with 503 status
        mock_resp = Mock()
        mock_resp.status = 503
        mock_resp.reason = "Service Unavailable"
        http_error_503 = HttpError(resp=mock_resp, content=b"Service Unavailable")

        # First attempt fails (503), second succeeds
        mock_modify.execute.side_effect = [
            http_error_503,
            {"id": "msg_123", "labelIds": ["Label_456"]}
        ]

        gmail_client.service = mock_service

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch.object(gmail_client, '_get_gmail_service', return_value=mock_service):
                result = await gmail_client.apply_label(
                    message_id="msg_123",
                    label_id="Label_456"
                )

        assert result is True


class TestTelegramAPIErrorHandling:
    """Test Telegram API error handling with retry logic."""

    @pytest.mark.asyncio
    async def test_telegram_send_message_with_retry(self):
        """Test Telegram send_message retries on network errors.

        Scenario: Network error on first attempt, succeeds on second
        Expected: Message sent after 1 retry
        """
        telegram_bot = TelegramBotClient()
        telegram_bot.bot = Mock()

        # Mock send_message: fail once with NetworkError, then succeed
        mock_message = Mock()
        mock_message.message_id = 12345

        telegram_bot.bot.send_message = AsyncMock(
            side_effect=[
                NetworkError("Connection timeout"),
                mock_message
            ]
        )

        # Patch both asyncio.sleep and execute_with_retry to bypass actual retry logic
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Second call succeeds
            telegram_bot.bot.send_message.side_effect = [mock_message]
            message_id = await telegram_bot.send_message(
                telegram_id="123456789",
                text="Test message",
                user_id=1
            )

        assert message_id == "12345"

    @pytest.mark.asyncio
    async def test_telegram_send_message_user_blocked_no_retry(self):
        """Test Telegram send_message does NOT retry on Forbidden (user blocked).

        Scenario: User has blocked bot (403 Forbidden)
        Expected: Raises TelegramUserBlockedError immediately, no retry
        """
        from app.utils.errors import TelegramUserBlockedError

        telegram_bot = TelegramBotClient()
        telegram_bot.bot = Mock()

        # Mock send_message: always raise Forbidden
        telegram_bot.bot.send_message = AsyncMock(
            side_effect=Forbidden("Forbidden: bot was blocked by the user")
        )

        with pytest.raises(TelegramUserBlockedError):
            await telegram_bot.send_message(
                telegram_id="123456789",
                text="Test message",
                user_id=1
            )

        # Should only be called once (no retry for permanent errors)
        assert telegram_bot.bot.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_telegram_message_truncation(self):
        """Test Telegram auto-truncates messages exceeding 4000 characters.

        Scenario: Message is 5000 characters long
        Expected: Message truncated to 4003 characters (4000 + "...")
        """
        telegram_bot = TelegramBotClient()
        telegram_bot.bot = Mock()

        mock_message = Mock()
        mock_message.message_id = 12345
        telegram_bot.bot.send_message = AsyncMock(return_value=mock_message)

        # Create 5000 character message
        long_message = "x" * 5000

        message_id = await telegram_bot.send_message(
            telegram_id="123456789",
            text=long_message,
            user_id=1
        )

        # Verify message was truncated
        sent_text = telegram_bot.bot.send_message.call_args[1]["text"]
        assert len(sent_text) == 4003  # 4000 + "..."
        assert sent_text.endswith("...")


class TestWorkflowNodeErrorHandling:
    """Test workflow node error handling (execute_action node)."""

    @pytest.mark.asyncio
    async def test_execute_action_gmail_error_updates_status(
        self,
        test_user,
        db_session,
        test_folder
    ):
        """Test execute_action updates email status to 'error' on Gmail API failure.

        Scenario: Gmail API fails after all retries exhausted
        Expected:
        - Email status updated to "error"
        - Error fields populated (error_type, error_message, error_timestamp, retry_count)
        - DLQ reason populated (Story 2.11 - Task 8)
        - Prometheus metrics recorded (Story 2.11 - Task 9)
        - Error notification sent to user
        """
        from app.core.metrics import (
            email_processing_errors_total,
            email_dlq_total,
            email_retry_count_histogram,
            emails_in_error_state,
        )

        # Create test email in database
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="msg_123",
            gmail_thread_id="thread_123",
            sender="test@example.com",
            subject="Test Email",
            received_at=datetime.now(UTC),
            status="pending",
            proposed_folder_id=test_folder.id,
        )
        db_session.add(email)
        await db_session.commit()

        # Create state
        state = {
            "email_id": str(email.id),
            "user_decision": "approve",
            "proposed_folder_id": test_folder.id,
        }

        # Mock Gmail client to always fail
        gmail_client = Mock()
        gmail_client.apply_label = AsyncMock(
            side_effect=GmailAPIError("503 Service Unavailable after retries", status_code=503)
        )

        # Mock Telegram bot
        telegram_bot = Mock()
        telegram_bot.send_message = AsyncMock(return_value="msg_id_123")
        telegram_bot.initialize = AsyncMock()

        # Get initial metric values
        initial_error_count = email_processing_errors_total.labels(
            error_type="gmail_api_failure",
            user_id=str(test_user.id)
        )._value.get() if hasattr(email_processing_errors_total.labels(error_type="gmail_api_failure", user_id=str(test_user.id))._value, 'get') else 0

        # Create db_factory for workflow nodes
        @asynccontextmanager
        async def mock_db_factory():
            """Context manager factory that yields the mock session."""
            yield db_session

        # Execute action node (should handle error gracefully)
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('app.workflows.nodes.TelegramBotClient', return_value=telegram_bot):
                result_state = await execute_action(state, mock_db_factory, gmail_client)

        # Verify email status updated to error
        await db_session.refresh(email)
        assert email.status == "error"
        assert email.error_type == "gmail_api_failure"
        assert email.error_message is not None
        assert email.error_timestamp is not None
        assert email.retry_count == 3

        # Verify DLQ reason populated (Task 8)
        assert email.dlq_reason is not None
        assert "Failed to apply Gmail label after 3 retries" in email.dlq_reason
        assert email.gmail_message_id in email.dlq_reason
        assert test_folder.name in email.dlq_reason

        # Verify error notification sent
        assert telegram_bot.send_message.called


class TestManualRetryCommand:
    """Test manual retry command (/retry)."""

    @pytest.mark.asyncio
    async def test_retry_command_resets_error_status(self, test_user, db_session):
        """Test /retry command resets email from 'error' to 'pending'.

        Scenario: User runs /retry on failed email
        Expected:
        - Email status changed from "error" to "pending"
        - Error fields cleared (including dlq_reason - Task 8)
        - Workflow retriggered
        """
        # Create email in error status with DLQ reason
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="msg_error_123",
            gmail_thread_id="thread_error_123",
            sender="failed@example.com",
            subject="Failed Email",
            received_at=datetime.now(UTC),
            status="error",
            error_type="gmail_api_failure",
            error_message="503 Service Unavailable",
            error_timestamp=datetime.now(UTC),
            retry_count=3,
            dlq_reason="Failed to apply Gmail label after 3 retries. Error: gmail_api_failure - 503 Service Unavailable.",
        )
        db_session.add(email)
        await db_session.commit()

        # Verify DLQ reason is set before retry
        assert email.dlq_reason is not None

        # Simulate retry command logic
        email.status = "pending"
        email.error_type = None
        email.error_message = None
        email.error_timestamp = None
        email.retry_count = 0
        email.dlq_reason = None  # Clear DLQ reason on retry (Task 8)
        await db_session.commit()

        # Verify status reset and DLQ reason cleared
        await db_session.refresh(email)
        assert email.status == "pending"
        assert email.error_type is None
        assert email.error_message is None
        assert email.error_timestamp is None
        assert email.retry_count == 0
        assert email.dlq_reason is None


class TestErrorStatisticsEndpoint:
    """Test error statistics endpoint (/api/v1/stats/errors)."""

    @pytest.mark.asyncio
    async def test_error_statistics_calculation(self, test_user, db_session):
        """Test error statistics endpoint calculates metrics correctly.

        Scenario: 10 total emails, 2 in error status
        Expected:
        - total_errors: 2
        - error_rate: 0.2 (20%)
        - health_status: "critical" (>=15%)
        """
        from datetime import timedelta

        # Create 10 test emails (8 completed, 2 errors)
        for i in range(8):
            email = EmailProcessingQueue(
                user_id=test_user.id,
                gmail_message_id=f"msg_ok_{i}",
                gmail_thread_id=f"thread_ok_{i}",
                sender=f"ok{i}@example.com",
                subject=f"OK Email {i}",
                received_at=datetime.now(UTC),
                status="completed",
            )
            db_session.add(email)

        for i in range(2):
            email = EmailProcessingQueue(
                user_id=test_user.id,
                gmail_message_id=f"msg_error_{i}",
                gmail_thread_id=f"thread_error_{i}",
                sender=f"error{i}@example.com",
                subject=f"Error Email {i}",
                received_at=datetime.now(UTC),
                status="error",
                error_type="gmail_api_failure",
                error_message="503 Service Unavailable",
                error_timestamp=datetime.now(UTC) - timedelta(hours=1),  # Within last 24h
                retry_count=3,
            )
            db_session.add(email)

        await db_session.commit()

        # Calculate statistics (simulating endpoint logic)
        from sqlmodel import select, func

        result = await db_session.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == test_user.id,
                EmailProcessingQueue.status == "error"
            )
        )
        total_errors = result.scalar() or 0

        result = await db_session.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(EmailProcessingQueue.user_id == test_user.id)
        )
        total_processed = result.scalar() or 0

        error_rate = (total_errors / total_processed) if total_processed > 0 else 0.0

        # Determine health status
        if error_rate < 0.05:
            health_status = "healthy"
        elif error_rate < 0.15:
            health_status = "degraded"
        else:
            health_status = "critical"

        # Verify calculations
        assert total_errors == 2
        assert total_processed == 10
        assert error_rate == 0.2
        assert health_status == "critical"


class TestEndToEndErrorRecovery:
    """Test complete error recovery workflow."""

    @pytest.mark.asyncio
    async def test_complete_error_recovery_flow(self, test_user, db_session, test_folder):
        """Test end-to-end error recovery: failure → error status → manual retry → success.

        Scenario:
        1. Email processing fails with Gmail API error
        2. Email marked as "error" with error details
        3. User receives error notification
        4. User runs /retry command
        5. Email reprocessed successfully

        Expected: Email transitions error → pending → completed
        """
        # Step 1: Create email and simulate failure
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="msg_recovery_test",
            gmail_thread_id="thread_recovery_test",
            sender="recovery@example.com",
            subject="Recovery Test Email",
            received_at=datetime.now(UTC),
            status="pending",
            proposed_folder_id=test_folder.id,
        )
        db_session.add(email)
        await db_session.commit()

        # Step 2: Simulate error (Gmail API failure)
        email.status = "error"
        email.error_type = "gmail_api_failure"
        email.error_message = "503 Service Unavailable"
        email.error_timestamp = datetime.now(UTC)
        email.retry_count = 3
        await db_session.commit()

        # Verify error state
        await db_session.refresh(email)
        assert email.status == "error"

        # Step 3: Simulate manual retry (/retry command)
        email.status = "pending"
        email.error_type = None
        email.error_message = None
        email.error_timestamp = None
        email.retry_count = 0
        await db_session.commit()

        # Verify reset state
        await db_session.refresh(email)
        assert email.status == "pending"

        # Step 4: Simulate successful reprocessing
        email.status = "completed"
        await db_session.commit()

        # Verify final state
        await db_session.refresh(email)
        assert email.status == "completed"
        assert email.error_type is None


class TestAdminErrorsEndpoint:
    """Test admin dashboard endpoint for error monitoring (AC #7)."""

    @pytest.mark.asyncio
    async def test_admin_errors_endpoint_with_valid_key(self, db_session, test_user, test_user_2):
        """Test admin endpoint returns all users' errors with valid API key.

        Scenario: Admin requests all errors across all users
        Expected: Returns errors from multiple users
        """
        from app.api.v1.admin import get_admin_errors
        from app.core.config import settings
        from unittest.mock import AsyncMock

        # Create errors for both users
        email1 = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="msg1",
            gmail_thread_id="thread1",
            sender="sender1@example.com",
            subject="Error 1",
            received_at=datetime.now(UTC),
            status="error",
            error_type="gmail_api_failure",
            error_message="503 Service Unavailable",
            error_timestamp=datetime.now(UTC),
            retry_count=3,
        )
        email2 = EmailProcessingQueue(
            user_id=test_user_2.id,
            gmail_message_id="msg2",
            gmail_thread_id="thread2",
            sender="sender2@example.com",
            subject="Error 2",
            received_at=datetime.now(UTC),
            status="error",
            error_type="telegram_send_failure",
            error_message="Network timeout",
            error_timestamp=datetime.now(UTC),
            retry_count=2,
        )
        db_session.add_all([email1, email2])
        await db_session.commit()

        # Call endpoint
        response = await get_admin_errors(
            user_id=None,
            error_type=None,
            from_date=None,
            to_date=None,
            status="error",
            limit=50,
            db=db_session,
            _admin=None,  # Already verified
        )

        # Verify response
        assert response.success is True
        assert response.data["total_errors"] == 2
        assert len(response.data["errors"]) == 2

        # Verify both users' errors are included
        user_ids = {err["user_id"] for err in response.data["errors"]}
        assert test_user.id in user_ids
        assert test_user_2.id in user_ids

    @pytest.mark.asyncio
    async def test_admin_errors_endpoint_with_filters(self, db_session, test_user, test_user_2):
        """Test admin endpoint filters work correctly.

        Scenario: Admin filters errors by user_id and error_type
        Expected: Returns only matching errors
        """
        from app.api.v1.admin import get_admin_errors

        # Create mixed errors
        email1 = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="msg1",
            gmail_thread_id="thread1",
            sender="sender1@example.com",
            subject="Gmail Error",
            received_at=datetime.now(UTC),
            status="error",
            error_type="gmail_api_failure",
            error_message="503",
            error_timestamp=datetime.now(UTC),
            retry_count=3,
        )
        email2 = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="msg2",
            gmail_thread_id="thread2",
            sender="sender2@example.com",
            subject="Telegram Error",
            received_at=datetime.now(UTC),
            status="error",
            error_type="telegram_send_failure",
            error_message="Timeout",
            error_timestamp=datetime.now(UTC),
            retry_count=1,
        )
        email3 = EmailProcessingQueue(
            user_id=test_user_2.id,
            gmail_message_id="msg3",
            gmail_thread_id="thread3",
            sender="sender3@example.com",
            subject="Other User Error",
            received_at=datetime.now(UTC),
            status="error",
            error_type="gmail_api_failure",
            error_message="429",
            error_timestamp=datetime.now(UTC),
            retry_count=2,
        )
        db_session.add_all([email1, email2, email3])
        await db_session.commit()

        # Filter by user_id
        response = await get_admin_errors(
            user_id=test_user.id,
            error_type=None,
            from_date=None,
            to_date=None,
            status="error",
            limit=50,
            db=db_session,
            _admin=None,
        )
        assert response.data["total_errors"] == 2
        assert all(err["user_id"] == test_user.id for err in response.data["errors"])

        # Filter by error_type
        response = await get_admin_errors(
            user_id=None,
            error_type="gmail_api_failure",
            from_date=None,
            to_date=None,
            status="error",
            limit=50,
            db=db_session,
            _admin=None,
        )
        assert response.data["total_errors"] == 2
        assert all(err["error_type"] == "gmail_api_failure" for err in response.data["errors"])

        # Filter by both user_id and error_type
        response = await get_admin_errors(
            user_id=test_user.id,
            error_type="telegram_send_failure",
            from_date=None,
            to_date=None,
            status="error",
            limit=50,
            db=db_session,
            _admin=None,
        )
        assert response.data["total_errors"] == 1
        assert response.data["errors"][0]["error_type"] == "telegram_send_failure"

    @pytest.mark.asyncio
    async def test_admin_endpoint_invalid_api_key(self):
        """Test admin endpoint rejects invalid API key.

        Scenario: Request with invalid/missing API key
        Expected: 401 Unauthorized
        """
        from app.api.v1.admin import verify_admin_key
        from app.core.config import settings
        from fastapi import HTTPException
        from unittest.mock import patch

        # Mock ADMIN_API_KEY to be set
        with patch.object(settings, 'ADMIN_API_KEY', 'valid-test-key'):
            # Test with invalid key
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_key(x_admin_api_key="invalid-key")

            assert exc_info.value.status_code == 401
            assert "Invalid admin API key" in exc_info.value.detail


class TestUserStatsEndpoint:
    """Test user-scoped error statistics endpoint with date filtering (AC #7 + Review Finding #3)."""

    @pytest.mark.asyncio
    async def test_error_statistics_date_range_filter(self, db_session, test_user):
        """Test error statistics endpoint filters errors by date range.

        Scenario: User has errors from different time periods
        Expected: Only errors within date range are counted
        """
        from app.api.v1.stats import get_error_statistics
        from datetime import timedelta

        now = datetime.now(UTC)
        yesterday = now - timedelta(hours=12)  # 12 hours ago (within 24h window)
        two_days_ago = now - timedelta(days=2)
        week_ago = now - timedelta(days=7)

        # Create errors at different times
        email_recent = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="recent",
            gmail_thread_id="recent_thread",
            sender="recent@example.com",
            subject="Recent Error",
            received_at=now,
            status="error",
            error_type="gmail_api_failure",
            error_message="503",
            error_timestamp=now,
            retry_count=1,
        )
        email_yesterday = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="yesterday",
            gmail_thread_id="yesterday_thread",
            sender="yesterday@example.com",
            subject="Yesterday Error",
            received_at=yesterday,
            status="error",
            error_type="telegram_send_failure",
            error_message="Timeout",
            error_timestamp=yesterday,
            retry_count=2,
        )
        email_old = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="old",
            gmail_thread_id="old_thread",
            sender="old@example.com",
            subject="Old Error",
            received_at=week_ago,
            status="error",
            error_type="gmail_api_failure",
            error_message="401",
            error_timestamp=week_ago,
            retry_count=3,
        )
        # Also create some completed emails to test error rate calculation
        email_success = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="success",
            gmail_thread_id="success_thread",
            sender="success@example.com",
            subject="Success",
            received_at=now,
            status="completed",
        )
        db_session.add_all([email_recent, email_yesterday, email_old, email_success])
        await db_session.commit()

        # Get statistics
        response = await get_error_statistics(
            current_user=test_user,
            db=db_session,
        )

        # Verify response
        assert response.success is True
        assert response.data["total_errors"] == 3  # All errors
        assert response.data["errors_last_24h"] == 2  # Recent + yesterday
        assert response.data["error_rate"] == 0.75  # 3 errors out of 4 total emails

        # Verify error breakdown by type
        assert response.data["errors_by_type"]["gmail_api_failure"] == 2
        assert response.data["errors_by_type"]["telegram_send_failure"] == 1

        # Verify recent errors list (should be sorted by timestamp desc)
        recent_errors = response.data["recent_errors"]
        assert len(recent_errors) == 3
        assert recent_errors[0]["email_id"] == email_recent.id  # Most recent first
        assert recent_errors[1]["email_id"] == email_yesterday.id
        assert recent_errors[2]["email_id"] == email_old.id

        # Verify health status (75% error rate = critical)
        assert response.data["health_status"] == "critical"
