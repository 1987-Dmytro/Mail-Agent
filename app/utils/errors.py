"""Custom exception classes for Mail Agent application.

These exceptions provide specific error types for better error handling
and more informative error messages throughout the application.
"""


class QuotaExceededError(Exception):
    """Raised when Gmail API quota is exceeded (429 Rate Limit).

    Gmail API has the following quotas:
    - 10,000 requests/day
    - 100 sends/day

    When this error is raised, the application should:
    1. Log the quota exceeded event
    2. Pause email sending operations
    3. Wait until quota reset (daily at midnight PT)

    Attributes:
        message: Error description
        retry_after: Seconds until quota reset (if available)
    """

    def __init__(self, message: str, retry_after: int = None):
        """Initialize QuotaExceededError.

        Args:
            message: Error description
            retry_after: Seconds until quota reset (optional)
        """
        super().__init__(message)
        self.retry_after = retry_after


class InvalidRecipientError(Exception):
    """Raised when recipient email address is invalid (400 Bad Request).

    This error occurs when:
    - Email format is invalid (missing @, invalid domain)
    - Recipient mailbox does not exist
    - Recipient domain does not exist

    The application should:
    1. Log the invalid recipient
    2. Return user-friendly error message
    3. Do not retry (permanent failure)

    Attributes:
        message: Error description
        recipient: The invalid recipient email address
    """

    def __init__(self, message: str, recipient: str = None):
        """Initialize InvalidRecipientError.

        Args:
            message: Error description
            recipient: The invalid recipient email (optional)
        """
        super().__init__(message)
        self.recipient = recipient


class MessageTooLargeError(Exception):
    """Raised when email message exceeds Gmail size limit (413 Request Entity Too Large).

    Gmail API limits:
    - Maximum message size: 25 MB (including attachments)
    - Maximum attachment size: 25 MB per attachment

    This error occurs when:
    - Email body + attachments exceed 25 MB
    - Single attachment exceeds 25 MB

    The application should:
    1. Log the oversized message
    2. Return user-friendly error with size info
    3. Do not retry (permanent failure)

    Attributes:
        message: Error description
        size_bytes: The message size in bytes (if available)
    """

    def __init__(self, message: str, size_bytes: int = None):
        """Initialize MessageTooLargeError.

        Args:
            message: Error description
            size_bytes: Message size in bytes (optional)
        """
        super().__init__(message)
        self.size_bytes = size_bytes


class GmailAPIError(Exception):
    """Base exception for Gmail API errors.

    This exception is raised when Gmail API operations fail.
    Common causes: network errors, authentication issues, API service errors.

    Attributes:
        message: Error description
        status_code: HTTP status code from Gmail API (if available)
    """

    def __init__(self, message: str, status_code: int = None):
        """Initialize GmailAPIError.

        Args:
            message: Error description
            status_code: HTTP status code (optional)
        """
        super().__init__(message)
        self.status_code = status_code


class GeminiAPIError(Exception):
    """Base exception for Google Gemini API errors.

    This exception serves as the parent class for all Gemini-specific errors.
    Use more specific subclasses when the error type is known.

    Attributes:
        message: Error description
        status_code: HTTP status code from Gemini API (if available)
    """

    def __init__(self, message: str, status_code: int = None):
        """Initialize GeminiAPIError.

        Args:
            message: Error description
            status_code: HTTP status code (optional)
        """
        super().__init__(message)
        self.status_code = status_code


class GeminiRateLimitError(GeminiAPIError):
    """Raised when Gemini API rate limit is exceeded (429 Too Many Requests).

    Gemini 2.5 Flash free tier limits:
    - 1,000,000 tokens/minute
    - Typically unlimited requests (token-based throttling)

    When this error is raised, the application should:
    1. Log the rate limit event with retry attempt
    2. Apply exponential backoff (2s, 4s, 8s delays)
    3. Retry up to 3 times before failing

    Attributes:
        message: Error description
        retry_after: Seconds until rate limit reset (if provided by API)
    """

    def __init__(self, message: str, retry_after: int = None):
        """Initialize GeminiRateLimitError.

        Args:
            message: Error description
            retry_after: Seconds until rate limit reset (optional)
        """
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class GeminiTimeoutError(GeminiAPIError):
    """Raised when Gemini API request times out.

    Default timeout is 30 seconds. Timeouts can occur due to:
    - Network connectivity issues
    - Gemini API service degradation
    - Very long prompt processing (rare with gemini-2.5-flash)

    The application should:
    1. Log the timeout with request context
    2. Retry with exponential backoff (transient error)
    3. Consider reducing prompt length if consistent timeouts

    Attributes:
        message: Error description
        timeout_seconds: The timeout value that was exceeded
    """

    def __init__(self, message: str, timeout_seconds: int = 30):
        """Initialize GeminiTimeoutError.

        Args:
            message: Error description
            timeout_seconds: Timeout value in seconds (default: 30)
        """
        super().__init__(message, status_code=408)
        self.timeout_seconds = timeout_seconds


class GeminiInvalidRequestError(GeminiAPIError):
    """Raised when Gemini API rejects request as invalid (400 Bad Request).

    This error occurs for permanent failures such as:
    - Blocked prompt (inappropriate content)
    - Invalid API key (403 Forbidden)
    - Malformed request parameters
    - Model not found or unavailable

    The application should:
    1. Log the error with prompt preview (first 100 chars)
    2. Do NOT retry (permanent error, retrying wastes quota)
    3. Return user-friendly error message
    4. Alert developer if API key issue (403)

    Attributes:
        message: Error description
        prompt_preview: First 100 chars of prompt (for debugging)
    """

    def __init__(self, message: str, prompt_preview: str = None):
        """Initialize GeminiInvalidRequestError.

        Args:
            message: Error description
            prompt_preview: First 100 chars of prompt (optional)
        """
        super().__init__(message, status_code=400)
        self.prompt_preview = prompt_preview


class TelegramBotError(Exception):
    """Base exception for Telegram bot errors.

    This exception serves as the parent class for all Telegram bot-specific errors.
    Use more specific subclasses when the error type is known.

    Attributes:
        message: Error description
    """

    def __init__(self, message: str):
        """Initialize TelegramBotError.

        Args:
            message: Error description
        """
        super().__init__(message)


class TelegramSendError(TelegramBotError):
    """Failed to send message via Telegram.

    This error occurs for transient failures such as:
    - Network connectivity issues
    - Telegram API service degradation
    - Rate limiting (though handled separately in production)

    The application should:
    1. Log the error with telegram_id and error details
    2. Retry with exponential backoff (transient error)
    3. Alert if persistent failures occur

    Attributes:
        message: Error description
    """

    pass


class TelegramUserBlockedError(TelegramBotError):
    """User has blocked the bot.

    This error occurs when the user has:
    - Blocked the bot in Telegram
    - Deleted their Telegram account
    - The bot was removed from the chat

    The application should:
    1. Log the blocked user event
    2. Update user record (telegram_id = null or flag as blocked)
    3. Do NOT retry sending (permanent failure)
    4. Notify user via email that Telegram notifications are disabled

    Attributes:
        message: Error description
    """

    pass
