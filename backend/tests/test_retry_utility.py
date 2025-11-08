"""Unit tests for retry utility with exponential backoff.

Tests cover:
1. Successful execution on first attempt (no retries needed)
2. Successful execution after transient failures (retries work)
3. All retries exhausted scenario (raises exception)
4. Exponential backoff delay calculation (2s, 4s, 8s, 16s cap)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, call
from requests.exceptions import RequestException, Timeout
from googleapiclient.errors import HttpError

from app.utils.retry import execute_with_retry, RetryConfig
from app.utils.errors import GmailAPIError, TelegramSendError


class TestRetryUtility:
    """Test suite for retry utility with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_execution_first_attempt(self):
        """Test successful execution on first attempt (no retries needed).

        Scenario: API call succeeds immediately
        Expected: Function returns result, no retry attempts logged
        """
        # Mock async function that succeeds immediately
        mock_func = AsyncMock(return_value="success")

        # Execute with retry
        result = await execute_with_retry(mock_func, "arg1", kwarg1="value")

        # Assert function called once
        assert mock_func.call_count == 1
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value")

    @pytest.mark.asyncio
    async def test_successful_execution_after_failures(self):
        """Test successful execution after 2 failed attempts.

        Scenario: API fails with 503 twice, then succeeds
        Expected: Function retries 2 times, returns result on 3rd attempt
        """
        # Mock function that fails twice then succeeds
        mock_func = AsyncMock(
            side_effect=[
                RequestException("503 Service Unavailable"),
                RequestException("503 Service Unavailable"),
                "success"  # Third attempt succeeds
            ]
        )

        # Execute with retry (should succeed after 2 retries)
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await execute_with_retry(mock_func)

        # Assert function called 3 times (1 initial + 2 retries)
        assert mock_func.call_count == 3
        assert result == "success"

        # Assert sleep called with correct delays (2s, 4s)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([
            call(2),  # First retry: 2 * (2^0) = 2s
            call(4),  # Second retry: 2 * (2^1) = 4s
        ])

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """Test all retries exhausted (raises exception).

        Scenario: API fails all 4 attempts (1 initial + 3 retries)
        Expected: Exception raised after MAX_RETRIES exhausted
        """
        # Mock function that always fails
        mock_func = AsyncMock(
            side_effect=GmailAPIError("503 Service Unavailable", status_code=503)
        )

        # Execute with retry (should exhaust retries and raise exception)
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(GmailAPIError) as exc_info:
                await execute_with_retry(mock_func)

        # Assert exception message
        assert "503 Service Unavailable" in str(exc_info.value)

        # Assert function called MAX_RETRIES + 1 times (1 initial + 3 retries)
        assert mock_func.call_count == RetryConfig.MAX_RETRIES + 1

        # Assert sleep called 3 times (for 3 retries)
        assert mock_sleep.call_count == RetryConfig.MAX_RETRIES
        mock_sleep.assert_has_calls([
            call(2),  # First retry: 2 * (2^0) = 2s
            call(4),  # Second retry: 2 * (2^1) = 4s
            call(8),  # Third retry: 2 * (2^2) = 8s
        ])

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation (2s, 4s, 8s, 16s cap).

        Scenario: Verify backoff delays follow exponential formula
        Expected: Delays are 2s, 4s, 8s, capped at 16s
        """
        # Mock function that fails multiple times
        mock_func = AsyncMock(
            side_effect=[
                Timeout("Network timeout"),
                Timeout("Network timeout"),
                Timeout("Network timeout"),
                Timeout("Network timeout"),  # Will raise after 3 retries
            ]
        )

        # Track sleep delays
        sleep_delays = []

        async def track_sleep(delay):
            sleep_delays.append(delay)

        with patch('asyncio.sleep', side_effect=track_sleep):
            with pytest.raises(Timeout):
                await execute_with_retry(mock_func)

        # Assert delays follow exponential backoff formula
        # Attempt 0 fails -> delay = min(2 * 2^0, 16) = 2s
        # Attempt 1 fails -> delay = min(2 * 2^1, 16) = 4s
        # Attempt 2 fails -> delay = min(2 * 2^2, 16) = 8s
        assert len(sleep_delays) == 3
        assert sleep_delays[0] == 2
        assert sleep_delays[1] == 4
        assert sleep_delays[2] == 8

    @pytest.mark.asyncio
    async def test_exponential_backoff_max_cap(self):
        """Test exponential backoff respects MAX_DELAY cap.

        Scenario: If formula exceeds MAX_DELAY (16s), cap at 16s
        Expected: Delay capped at 16 seconds
        """
        # Temporarily increase MAX_RETRIES to test capping
        original_max_retries = RetryConfig.MAX_RETRIES
        RetryConfig.MAX_RETRIES = 5  # Test more retries to hit cap

        # Mock function that fails 6 times
        mock_func = AsyncMock(
            side_effect=[TelegramSendError("Network error")] * 6
        )

        sleep_delays = []

        async def track_sleep(delay):
            sleep_delays.append(delay)

        with patch('asyncio.sleep', side_effect=track_sleep):
            with pytest.raises(TelegramSendError):
                await execute_with_retry(mock_func)

        # Assert delays: 2, 4, 8, 16, 16 (capped at MAX_DELAY)
        # Attempt 0 fails -> delay = min(2 * 2^0, 16) = 2s
        # Attempt 1 fails -> delay = min(2 * 2^1, 16) = 4s
        # Attempt 2 fails -> delay = min(2 * 2^2, 16) = 8s
        # Attempt 3 fails -> delay = min(2 * 2^3, 16) = 16s (2^3 = 8, 2*8 = 16)
        # Attempt 4 fails -> delay = min(2 * 2^4, 16) = 16s (2^4 = 16, 2*16 = 32, capped at 16)
        assert len(sleep_delays) == 5
        assert sleep_delays[0] == 2
        assert sleep_delays[1] == 4
        assert sleep_delays[2] == 8
        assert sleep_delays[3] == 16
        assert sleep_delays[4] == 16  # Capped at MAX_DELAY

        # Restore original MAX_RETRIES
        RetryConfig.MAX_RETRIES = original_max_retries

    @pytest.mark.asyncio
    async def test_http_error_retry(self):
        """Test retry logic with Gmail API HttpError.

        Scenario: Gmail API returns 503 HttpError
        Expected: Function retries and eventually succeeds
        """
        # Create proper mock response for HttpError
        from unittest.mock import Mock
        mock_response = Mock()
        mock_response.status = 503
        mock_response.reason = 'Service Unavailable'

        # Mock HttpError (503 Service Unavailable)
        http_error = HttpError(
            resp=mock_response,
            content=b'Service Unavailable'
        )

        # Mock function that fails once with HttpError then succeeds
        mock_func = AsyncMock(
            side_effect=[http_error, "success"]
        )

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await execute_with_retry(mock_func)

        assert mock_func.call_count == 2
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_exception_types(self):
        """Test retry handles different exception types.

        Scenario: Mix of RequestException, Timeout, GmailAPIError
        Expected: All exceptions caught and retried
        """
        # Mock function with different exception types
        mock_func = AsyncMock(
            side_effect=[
                RequestException("Connection error"),
                Timeout("Request timeout"),
                GmailAPIError("Service error", status_code=503),
                "success"
            ]
        )

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await execute_with_retry(mock_func)

        assert mock_func.call_count == 4
        assert result == "success"

    @pytest.mark.asyncio
    async def test_sync_function_wrapper(self):
        """Test retry utility works with sync functions (wrapped in async).

        Scenario: Pass sync function to execute_with_retry
        Expected: Function executed successfully (wrapped automatically)
        """
        # Regular sync function
        def sync_func(arg):
            return f"sync_{arg}"

        result = await execute_with_retry(sync_func, "test")

        assert result == "sync_test"
