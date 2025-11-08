"""Mock Gmail API client for integration testing.

This mock provides deterministic responses for testing Gmail operations
without making real API calls to Google Gmail API.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC


class GmailAPIError(Exception):
    """Mock Gmail API error for testing error scenarios."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class MockGmailClient:
    """Mock implementation of Gmail API client for testing.

    Tracks all Gmail operations (get message, apply label, send email)
    for test assertions.
    """

    def __init__(self):
        """Initialize mock with empty tracking."""
        self.applied_labels: List[Dict[str, Any]] = []
        self.sent_emails: List[Dict[str, Any]] = []
        self.get_message_calls: List[str] = []
        self._messages: Dict[str, Dict[str, Any]] = {}
        self._simulate_failures: List[str] = []
        self._failure_exception: Exception | None = None
        self._failure_count: int = 0
        self._current_call_count: int = 0

    def add_test_message(self, message_id: str, message_data: Dict[str, Any]):
        """Add a test message to be retrieved by get_message.

        Args:
            message_id: Gmail message ID
            message_data: Message metadata and body
        """
        self._messages[message_id] = message_data

    def simulate_failure(self, operation: str):
        """Configure mock to simulate API failure for specific operation.

        Args:
            operation: Operation to fail ('get_message', 'apply_label', 'send_email')
        """
        self._simulate_failures.append(operation)

    def set_failure_mode(self, exception: Exception, fail_count: int):
        """Configure mock to raise exceptions for testing error handling.

        Args:
            exception: Exception to raise on API calls
            fail_count: Number of calls that should fail before succeeding
        """
        self._failure_exception = exception
        self._failure_count = fail_count
        self._current_call_count = 0

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Mock get_message operation.

        Args:
            message_id: Gmail message ID to retrieve

        Returns:
            dict: Message metadata and body

        Raises:
            GmailAPIError: If simulate_failure was called for this operation
        """
        self.get_message_calls.append(message_id)

        # Handle failure mode (newer test pattern)
        self._current_call_count += 1
        if self._failure_exception and self._current_call_count <= self._failure_count:
            raise self._failure_exception

        # Handle old simulate_failure pattern
        if "get_message" in self._simulate_failures:
            raise GmailAPIError("503 Service Unavailable", status_code=503)

        # Return test message if configured, otherwise return default
        if message_id in self._messages:
            return self._messages[message_id]

        return {
            "id": message_id,
            "threadId": f"thread_{message_id}",
            "snippet": "Test email snippet",
            "internalDate": int(datetime.now(UTC).timestamp() * 1000),
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Email Subject"},
                    {"name": "Date", "value": "Mon, 1 Jan 2025 12:00:00 +0000"}
                ],
                "body": {
                    "data": "VGVzdCBlbWFpbCBib2R5IGNvbnRlbnQ="  # Base64 "Test email body content"
                }
            }
        }

    async def get_message_detail(self, message_id: str) -> Dict[str, Any]:
        """Mock get_message_detail operation (alias for get_message).

        This method exists to match the real GmailClient API which uses
        get_message_detail instead of get_message.

        Args:
            message_id: Gmail message ID to retrieve

        Returns:
            dict: Message metadata and body

        Raises:
            GmailAPIError: If simulate_failure was called for this operation
        """
        return await self.get_message(message_id)

    async def apply_label(self, message_id: str, label_id: str) -> bool:
        """Mock apply_label operation.

        Args:
            message_id: Gmail message ID
            label_id: Gmail label ID to apply

        Returns:
            bool: True if successful

        Raises:
            GmailAPIError: If simulate_failure was called for this operation
        """
        # Handle failure mode (newer test pattern)
        self._current_call_count += 1
        if self._failure_exception and self._current_call_count <= self._failure_count:
            raise self._failure_exception

        # Handle old simulate_failure pattern
        if "apply_label" in self._simulate_failures:
            raise GmailAPIError("503 Service Unavailable", status_code=503)

        # Track label application
        self.applied_labels.append({
            "message_id": message_id,
            "label_id": label_id,
            "timestamp": datetime.now(UTC)
        })
        return True

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None
    ) -> str:
        """Mock send_email operation.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            from_email: Sender email address (optional)

        Returns:
            str: Mock message ID of sent email

        Raises:
            GmailAPIError: If simulate_failure was called for this operation
        """
        if "send_email" in self._simulate_failures:
            raise GmailAPIError("429 Rate Limit Exceeded", status_code=429)

        # Generate mock message ID
        message_id = f"sent_msg_{len(self.sent_emails) + 1}"

        # Track sent email
        self.sent_emails.append({
            "message_id": message_id,
            "to": to,
            "from": from_email or "noreply@example.com",
            "subject": subject,
            "body": body,
            "timestamp": datetime.now(UTC)
        })

        return message_id

    def get_applied_labels(self, message_id: str) -> List[str]:
        """Get all labels applied to a specific message.

        Args:
            message_id: Gmail message ID

        Returns:
            list: List of label IDs applied to this message
        """
        return [
            label["label_id"]
            for label in self.applied_labels
            if label["message_id"] == message_id
        ]

    def get_sent_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a sent email by message ID.

        Args:
            message_id: Message ID of sent email

        Returns:
            dict or None: Email details if found
        """
        for email in self.sent_emails:
            if email["message_id"] == message_id:
                return email
        return None

    def reset(self):
        """Clear all tracking data."""
        self.applied_labels.clear()
        self.sent_emails.clear()
        self.get_message_calls.clear()
        self._simulate_failures.clear()
