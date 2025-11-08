"""Retry utility with exponential backoff for external API calls.

This module provides a retry mechanism for transient failures when calling
external APIs (Gmail, Telegram, Gemini). Uses exponential backoff to avoid
overwhelming failing services.

Retry Configuration:
- MAX_RETRIES: 3 attempts
- BASE_DELAY: 2 seconds
- MAX_DELAY: 16 seconds
- Exponential formula: min(BASE_DELAY * (2 ** attempt), MAX_DELAY)

Retry Delays:
- Attempt 1 failure: 2s delay
- Attempt 2 failure: 4s delay
- Attempt 3 failure: 8s delay
- Attempt 4 failure: 16s delay (capped)

Usage:
    from app.utils.retry import execute_with_retry

    # Retry an async function
    result = await execute_with_retry(
        some_api_call,
        arg1,
        arg2,
        kwarg1="value"
    )

    # The function will retry on transient errors (503, 429, timeout)
    # and raise exception after max retries exhausted
"""

import asyncio
from typing import Callable, Any, TypeVar
import structlog
from requests.exceptions import RequestException, Timeout
from googleapiclient.errors import HttpError

from app.utils.errors import (
    GmailAPIError,
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    TelegramSendError,
)
from app.core.metrics import email_retry_attempts_total


logger = structlog.get_logger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Retry configuration for external API calls.

    These values are set based on Epic 2 technical specification
    and provide optimal balance between quick recovery and not
    overwhelming failing services.
    """
    MAX_RETRIES = 3
    BASE_DELAY = 2  # seconds
    MAX_DELAY = 16  # seconds
    EXPONENTIAL_BASE = 2


async def execute_with_retry(
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """Execute async function with retry logic and exponential backoff.

    Retries transient failures (network errors, service unavailable, rate limits)
    up to MAX_RETRIES times with exponential backoff. Permanent errors (401 after
    token refresh, 403 user blocked) are not retried.

    Args:
        func: Async callable to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result from func if successful

    Raises:
        Exception: The last exception after all retries exhausted

    Example:
        result = await execute_with_retry(
            gmail_client.apply_label,
            email_id="123",
            label_id="Label_456"
        )
    """
    last_exception = None
    function_name = getattr(func, '__name__', str(func))

    for attempt in range(RetryConfig.MAX_RETRIES + 1):
        try:
            # Try executing the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Wrap sync function in async
                result = func(*args, **kwargs)

            # Success! Log if this was a retry
            if attempt > 0:
                logger.info(
                    "retry_success",
                    function_name=function_name,
                    attempt_number=attempt + 1,
                    max_retries=RetryConfig.MAX_RETRIES,
                )

                # Record successful retry in Prometheus (Story 2.11 - Task 9)
                email_retry_attempts_total.labels(
                    operation=function_name,
                    success="true"
                ).inc()

            return result

        except (
            RequestException,
            Timeout,
            TimeoutError,
            HttpError,
            GmailAPIError,
            GeminiAPIError,
            GeminiRateLimitError,
            GeminiTimeoutError,
            TelegramSendError,
            ConnectionError,
        ) as e:
            last_exception = e

            # Determine error type for logging
            error_type = type(e).__name__
            error_message = str(e)

            # Check if we've exhausted retries
            if attempt >= RetryConfig.MAX_RETRIES:
                logger.error(
                    "retry_exhausted",
                    function_name=function_name,
                    attempt_number=attempt + 1,
                    max_retries=RetryConfig.MAX_RETRIES,
                    error_type=error_type,
                    error_message=error_message,
                )

                # Record failed retry in Prometheus (Story 2.11 - Task 9)
                email_retry_attempts_total.labels(
                    operation=function_name,
                    success="false"
                ).inc()

                raise e

            # Calculate exponential backoff delay
            delay = min(
                RetryConfig.BASE_DELAY * (RetryConfig.EXPONENTIAL_BASE ** attempt),
                RetryConfig.MAX_DELAY
            )

            # Log retry attempt
            logger.warning(
                "retry_attempt",
                function_name=function_name,
                attempt_number=attempt + 1,
                max_retries=RetryConfig.MAX_RETRIES,
                delay_seconds=delay,
                error_type=error_type,
                error_message=error_message,
            )

            # Wait before retry
            await asyncio.sleep(delay)

    # Should never reach here, but raise last exception if we do
    if last_exception:
        raise last_exception
    raise RuntimeError(f"execute_with_retry failed for {function_name} with no exception")
