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
