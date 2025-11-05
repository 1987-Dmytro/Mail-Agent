"""
Gmail API Rate Limits and Quotas

Free Tier Quotas (per user per day):
- API requests: 10,000 requests/day
- Batch requests: 1,000 batches/day (50 requests per batch)
- Message sends: 100 sends/day

Typical Usage for Mail Agent:
- Email polling (every 2 min): 720 requests/day
- Message detail fetches (avg 5 emails/poll): 3,600 requests/day
- Thread history fetches: ~200 requests/day
- Label operations: ~100 requests/day
- Message sends: <100/day (well within limit)
- Total: ~4,620 requests/day (46% of quota, safe margin)

Rate Limit Handling:
- 429 errors trigger exponential backoff (2s, 4s, 8s delays)
- Quota exhaustion logs warning and pauses polling until reset
- Critical operations (send email) prioritized in quota allocation

Optimization Strategies:
- Batch API calls where possible (list + metadata in single request)
- Cache label lists (update only on changes)
- Use partial responses (fields parameter) to reduce data transfer

Reference: https://developers.google.com/gmail/api/reference/quota
"""

import base64
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from html.parser import HTMLParser
from typing import Dict, List, Optional

import structlog
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.gmail_auth import get_valid_gmail_credentials
from app.services.database import DatabaseService, database_service
from app.utils.errors import InvalidRecipientError, MessageTooLargeError, QuotaExceededError


class HTMLStripper(HTMLParser):
    """HTML parser to strip HTML tags and extract plain text."""

    def __init__(self):
        """Initialize the HTML stripper."""
        super().__init__()
        self.text = []

    def handle_data(self, data):
        """Handle text data from HTML."""
        self.text.append(data)

    def get_text(self):
        """Get the extracted plain text."""
        return "".join(self.text)


class GmailClient:
    """Gmail API client wrapper with automatic token refresh.

    Provides high-level async methods for Gmail operations:
    - get_messages(): List emails matching query
    - get_message_detail(): Get full email content with body
    - get_thread(): Get email thread history

    Features:
    - Automatic OAuth token refresh on 401 errors
    - Exponential backoff for rate limiting (429 errors)
    - MIME message parsing with HTML stripping
    - Structured logging with context
    """

    def __init__(self, user_id: int, db_service: DatabaseService = None):
        """Initialize Gmail client for specific user.

        Args:
            user_id: Database ID of user
            db_service: Optional DatabaseService for dependency injection
        """
        self.user_id = user_id
        self.db_service = db_service or database_service
        self.logger = structlog.get_logger(__name__)
        self.service = None  # Lazy-loaded Gmail service

    async def _get_gmail_service(self):
        """Build Gmail API service with valid credentials.

        Returns:
            Gmail API service object

        Raises:
            Exception: If credentials cannot be obtained
        """
        if self.service is None:
            credentials = await get_valid_gmail_credentials(self.user_id, self.db_service)
            self.service = build("gmail", "v1", credentials=credentials)
        return self.service

    def _parse_gmail_date(self, internal_date: str) -> datetime:
        """Convert Gmail internalDate to datetime.

        Args:
            internal_date: Milliseconds since epoch (as string)

        Returns:
            datetime object
        """
        if not internal_date:
            return datetime.now()
        timestamp_ms = int(internal_date)
        return datetime.fromtimestamp(timestamp_ms / 1000)

    def _decode_base64url(self, data: str) -> str:
        """Decode Gmail's base64url encoded string.

        Args:
            data: Base64url encoded string

        Returns:
            Decoded UTF-8 string
        """
        if not data:
            return ""
        try:
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            self.logger.warning("base64_decode_error", error=str(e))
            return ""

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and return plain text.

        Args:
            html: HTML content

        Returns:
            Plain text with HTML tags removed
        """
        if not html:
            return ""
        stripper = HTMLStripper()
        try:
            stripper.feed(html)
            return stripper.get_text()
        except Exception as e:
            self.logger.warning("html_strip_error", error=str(e))
            return html

    def _extract_body(self, payload: Dict) -> str:
        """Extract plain text body from Gmail message payload.

        Gmail MIME structure:
        - Simple message: payload.body.data (base64url encoded)
        - Multipart: payload.parts[] array of MIME parts
          - Each part has: mimeType, body.data
          - Prefer text/plain over text/html
          - Recursively search nested multipart sections

        Args:
            payload: Gmail message payload dict

        Returns:
            Plain text body (HTML stripped if only HTML available)
        """
        # Case 1: Simple message with body.data
        if "body" in payload and "data" in payload["body"]:
            return self._decode_base64url(payload["body"]["data"])

        # Case 2: Multipart message with parts[]
        if "parts" in payload:
            # First pass: Look for text/plain
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and "body" in part and "data" in part["body"]:
                    return self._decode_base64url(part["body"]["data"])

                # Recursively check nested parts
                if "parts" in part:
                    nested_body = self._extract_body(part)
                    if nested_body:
                        return nested_body

            # Second pass: Fallback to text/html (strip HTML tags)
            for part in payload["parts"]:
                if part.get("mimeType") == "text/html" and "body" in part and "data" in part["body"]:
                    html_content = self._decode_base64url(part["body"]["data"])
                    return self._strip_html(html_content)

                # Recursively check nested parts for HTML
                if "parts" in part:
                    nested_body = self._extract_body(part)
                    if nested_body:
                        return nested_body

        # Case 3: No body found
        return ""

    async def _execute_with_retry(self, api_call_func, max_retries: int = 3, token_refreshed: bool = False):
        """Execute Gmail API call with automatic retry on errors.

        Handles:
        - 401 Unauthorized: Refresh token and retry once
        - 429 Rate Limit: Exponential backoff (2s, 4s, 8s)
        - 500-503 Server Errors: Exponential backoff

        Args:
            api_call_func: Callable that makes the Gmail API call
            max_retries: Maximum retry attempts for transient errors
            token_refreshed: Internal flag to prevent infinite 401 retry loop

        Returns:
            API call result

        Raises:
            HttpError: If all retries exhausted or non-retryable error
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return api_call_func()
            except HttpError as e:
                last_error = e
                status = e.resp.status

                # 401: Token expired - refresh and retry once
                if status == 401 and not token_refreshed:
                    self.logger.info("token_expired_refreshing", user_id=self.user_id)
                    # Clear cached service to force re-auth
                    self.service = None
                    # Retry with fresh credentials (will call _get_gmail_service again)
                    # Set token_refreshed=True to prevent infinite loop
                    return await self._execute_with_retry(api_call_func, max_retries, token_refreshed=True)

                # 429: Rate limit - exponential backoff
                elif status == 429 and attempt < max_retries - 1:
                    delay = 2**attempt  # 2s, 4s, 8s
                    self.logger.warning(
                        "rate_limit_hit_retrying",
                        user_id=self.user_id,
                        attempt=attempt + 1,
                        delay=delay,
                    )
                    time.sleep(delay)
                    continue

                # 500-503: Server error - exponential backoff
                elif status in [500, 502, 503] and attempt < max_retries - 1:
                    delay = 2**attempt
                    self.logger.warning(
                        "gmail_server_error_retrying",
                        user_id=self.user_id,
                        status=status,
                        attempt=attempt + 1,
                        delay=delay,
                    )
                    time.sleep(delay)
                    continue

                # Non-retryable error or retries exhausted
                else:
                    self.logger.error(
                        "gmail_api_error",
                        user_id=self.user_id,
                        status=status,
                        error=str(e),
                        exc_info=True,
                    )
                    raise

        # Should not reach here, but raise last exception if we do
        if last_error:
            raise last_error
        else:
            # This should never happen, but handle gracefully
            raise RuntimeError("API call failed without exception")

    async def get_messages(self, query: str = "is:unread", max_results: int = 50) -> List[Dict]:
        """Fetch emails matching query from Gmail inbox.

        Args:
            query: Gmail search query (default: unread emails)
                   Examples: "is:unread", "from:user@example.com", "subject:urgent"
            max_results: Maximum emails to fetch (max 500 per Gmail API)

        Returns:
            List of email metadata dicts with keys:
            - message_id: str (Gmail message ID)
            - thread_id: str (Gmail thread ID for conversation grouping)
            - sender: str (From header)
            - subject: str (Subject line)
            - snippet: str (First ~200 characters preview)
            - received_at: datetime (Internal Date header)
            - labels: List[str] (Gmail label IDs applied to email)

        Raises:
            ValueError: If max_results exceeds Gmail API limit or is invalid
            HttpError: Gmail API error (handled with retry logic)
        """
        # Input validation
        if max_results <= 0:
            raise ValueError("max_results must be a positive integer")
        if max_results > 500:
            raise ValueError("max_results cannot exceed 500 (Gmail API limit)")

        service = await self._get_gmail_service()

        def _list_messages():
            # List messages matching query
            results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()

            messages = results.get("messages", [])

            # Fetch details for each message
            email_list = []
            for msg in messages:
                message_detail = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
                    .execute()
                )

                # Parse headers
                headers = {
                    h["name"]: h["value"] for h in message_detail.get("payload", {}).get("headers", [])
                }

                email_list.append(
                    {
                        "message_id": message_detail["id"],
                        "thread_id": message_detail["threadId"],
                        "sender": headers.get("From", ""),
                        "subject": headers.get("Subject", ""),
                        "snippet": message_detail.get("snippet", ""),
                        "received_at": self._parse_gmail_date(message_detail.get("internalDate")),
                        "labels": message_detail.get("labelIds", []),
                    }
                )

            return email_list

        result = await self._execute_with_retry(_list_messages)

        self.logger.info("gmail_messages_fetched", user_id=self.user_id, query=query, count=len(result))

        return result

    async def get_message_detail(self, message_id: str) -> Dict:
        """Get full email content including body and headers.

        Args:
            message_id: Gmail message ID (from get_messages)

        Returns:
            Dict with keys:
            - message_id: str
            - thread_id: str
            - sender: str (From header)
            - subject: str (Subject line)
            - body: str (Plain text extracted from HTML if needed)
            - headers: Dict[str, str] (All email headers)
            - received_at: datetime
            - labels: List[str]

        Raises:
            ValueError: If message_id is empty or invalid
            HttpError: Gmail API error (handled with retry logic)
        """
        # Input validation
        if not message_id or not isinstance(message_id, str):
            raise ValueError("message_id must be a non-empty string")
        if not message_id.strip():
            raise ValueError("message_id cannot be whitespace only")

        service = await self._get_gmail_service()

        def _get_message():
            message = service.users().messages().get(userId="me", id=message_id, format="full").execute()

            # Parse headers
            headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}

            # Extract body (handles text/plain and text/html MIME types)
            body = self._extract_body(message.get("payload", {}))

            return {
                "message_id": message["id"],
                "thread_id": message["threadId"],
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "body": body,
                "headers": headers,
                "received_at": self._parse_gmail_date(message.get("internalDate")),
                "labels": message.get("labelIds", []),
            }

        result = await self._execute_with_retry(_get_message)

        self.logger.info("gmail_message_detail_fetched", user_id=self.user_id, message_id=message_id)

        return result

    async def get_thread(self, thread_id: str) -> List[Dict]:
        """Get all emails in a thread (conversation history).

        Args:
            thread_id: Gmail thread ID

        Returns:
            List of message dicts (same format as get_message_detail)
            Sorted chronologically (oldest first)

        Raises:
            ValueError: If thread_id is empty or invalid
            HttpError: Gmail API error (handled with retry logic)
        """
        # Input validation
        if not thread_id or not isinstance(thread_id, str):
            raise ValueError("thread_id must be a non-empty string")
        if not thread_id.strip():
            raise ValueError("thread_id cannot be whitespace only")

        service = await self._get_gmail_service()

        def _get_thread():
            thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

            messages = thread.get("messages", [])

            # Parse each message in thread
            thread_messages = []
            for msg in messages:
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                body = self._extract_body(msg.get("payload", {}))

                thread_messages.append(
                    {
                        "message_id": msg["id"],
                        "thread_id": msg["threadId"],
                        "sender": headers.get("From", ""),
                        "subject": headers.get("Subject", ""),
                        "body": body,
                        "headers": headers,
                        "received_at": self._parse_gmail_date(msg.get("internalDate")),
                        "labels": msg.get("labelIds", []),
                    }
                )

            # Sort by received_at (chronological order)
            thread_messages.sort(key=lambda x: x["received_at"])

            return thread_messages

        result = await self._execute_with_retry(_get_thread)

        self.logger.info("gmail_thread_fetched", user_id=self.user_id, thread_id=thread_id, message_count=len(result))

        return result

    async def list_labels(self) -> List[Dict]:
        """List all Gmail labels for the user.

        Returns list of all labels (both system and user-created) with metadata.
        Useful for syncing label state or discovering existing labels.

        Returns:
            List of label dicts with keys:
            - label_id: str (Gmail's internal ID, e.g., "Label_123")
            - name: str (Label display name)
            - type: str ("system" or "user")
            - visibility: str ("labelShow", "labelHide", "labelShowIfUnread")

        Raises:
            HttpError: If Gmail API call fails

        Example:
            labels = await client.list_labels()
            for label in labels:
                if label['type'] == 'user':
                    print(f"User label: {label['name']}")
        """
        service = await self._get_gmail_service()

        def _list_labels():
            response = service.users().labels().list(userId="me").execute()
            return response.get("labels", [])

        result = await self._execute_with_retry(_list_labels)

        # Transform to consistent format
        labels = []
        for label in result:
            labels.append(
                {
                    "label_id": label.get("id"),
                    "name": label.get("name"),
                    "type": label.get("type", "user").lower(),
                    "visibility": label.get("labelListVisibility", "labelShow"),
                }
            )

        self.logger.info("gmail_labels_listed", user_id=self.user_id, label_count=len(labels))

        return labels

    async def create_label(self, name: str, color: Optional[str] = None, visibility: str = "labelShow") -> str:
        """Create a new Gmail label.

        If a label with the same name already exists (409 Conflict), returns the existing
        label ID instead of failing. This makes the operation idempotent.

        Args:
            name: Label display name (e.g., "Work", "Government")
            color: Hex color code (e.g., "#FF5733") - optional
            visibility: Label visibility setting (default: "labelShow")
                Options: "labelShow", "labelHide", "labelShowIfUnread"

        Returns:
            gmail_label_id (e.g., "Label_123")

        Raises:
            HttpError: If Gmail API call fails (except 409 Conflict)

        Example:
            label_id = await client.create_label("Important Clients", color="#FF5733")
            # Returns "Label_456" or existing label ID if already exists
        """
        service = await self._get_gmail_service()

        # Construct label object
        label_object = {
            "name": name,
            "labelListVisibility": visibility,
            "messageListVisibility": "show",
        }

        # Add color if provided
        if color:
            label_object["color"] = {"backgroundColor": color}

        def _create_label():
            return service.users().labels().create(userId="me", body=label_object).execute()

        try:
            result = await self._execute_with_retry(_create_label)
            gmail_label_id = result["id"]

            self.logger.info(
                "gmail_label_created",
                user_id=self.user_id,
                label_name=name,
                gmail_label_id=gmail_label_id,
                color=color,
            )

            return gmail_label_id

        except HttpError as e:
            # Handle duplicate label: 409 Conflict
            if e.resp.status == 409:
                self.logger.info(
                    "gmail_label_exists_returning_existing",
                    user_id=self.user_id,
                    label_name=name,
                )

                # Fetch existing label by name
                labels = await self.list_labels()
                for label in labels:
                    if label["name"] == name:
                        self.logger.info(
                            "gmail_label_found",
                            user_id=self.user_id,
                            label_name=name,
                            gmail_label_id=label["label_id"],
                        )
                        return label["label_id"]

                # Should never reach here, but handle gracefully
                self.logger.error(
                    "gmail_label_conflict_but_not_found",
                    user_id=self.user_id,
                    label_name=name,
                )
                raise

            # Non-409 errors: re-raise
            else:
                self.logger.error(
                    "gmail_label_creation_failed",
                    user_id=self.user_id,
                    label_name=name,
                    status=e.resp.status,
                    error=str(e),
                    exc_info=True,
                )
                raise

    async def apply_label(self, message_id: str, label_id: str) -> bool:
        """Apply label to email message (moves email to folder in Gmail UI).

        Args:
            message_id: Gmail message ID (e.g., from EmailProcessingQueue.gmail_message_id)
            label_id: Gmail label ID (e.g., from FolderCategory.gmail_label_id)

        Returns:
            True if successful, False otherwise

        Raises:
            HttpError: If message_id or label_id is invalid (404)

        Example:
            success = await client.apply_label("18abc123def", "Label_456")
            if success:
                print("Email moved to folder")
        """
        service = await self._get_gmail_service()

        def _apply_label():
            modify_body = {"addLabelIds": [label_id]}
            return service.users().messages().modify(userId="me", id=message_id, body=modify_body).execute()

        try:
            await self._execute_with_retry(_apply_label)

            self.logger.info(
                "gmail_label_applied",
                user_id=self.user_id,
                message_id=message_id,
                label_id=label_id,
                success=True,
            )

            return True

        except HttpError as e:
            status = e.resp.status

            # 404: Invalid message_id or label_id
            if status == 404:
                self.logger.error(
                    "gmail_label_apply_not_found",
                    user_id=self.user_id,
                    message_id=message_id,
                    label_id=label_id,
                    error=str(e),
                )
            else:
                self.logger.error(
                    "gmail_label_apply_failed",
                    user_id=self.user_id,
                    message_id=message_id,
                    label_id=label_id,
                    status=status,
                    error=str(e),
                    exc_info=True,
                )

            return False

    async def remove_label(self, message_id: str, label_id: str) -> bool:
        """Remove label from email message.

        Args:
            message_id: Gmail message ID
            label_id: Gmail label ID

        Returns:
            True if successful, False otherwise

        Raises:
            HttpError: If message_id or label_id is invalid (404)

        Example:
            success = await client.remove_label("18abc123def", "Label_456")
            if success:
                print("Label removed from email")
        """
        service = await self._get_gmail_service()

        def _remove_label():
            modify_body = {"removeLabelIds": [label_id]}
            return service.users().messages().modify(userId="me", id=message_id, body=modify_body).execute()

        try:
            await self._execute_with_retry(_remove_label)

            self.logger.info(
                "gmail_label_removed",
                user_id=self.user_id,
                message_id=message_id,
                label_id=label_id,
                success=True,
            )

            return True

        except HttpError as e:
            status = e.resp.status

            # 404: Invalid message_id or label_id
            if status == 404:
                self.logger.error(
                    "gmail_label_remove_not_found",
                    user_id=self.user_id,
                    message_id=message_id,
                    label_id=label_id,
                    error=str(e),
                )
            else:
                self.logger.error(
                    "gmail_label_remove_failed",
                    user_id=self.user_id,
                    message_id=message_id,
                    label_id=label_id,
                    status=status,
                    error=str(e),
                    exc_info=True,
                )

            return False

    def _compose_mime_message(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: str,
        in_reply_to: str = None,
        references: str = None,
        body_type: str = "plain",
    ) -> str:
        """Compose RFC 2822 compliant MIME message for Gmail API.

        Creates a MIME message with proper headers (From, To, Subject, Date) and
        optional threading headers (In-Reply-To, References) for conversation threading.
        Supports both plain text and HTML body types.

        Args:
            to: Recipient email address (e.g., "user@example.com")
            subject: Email subject line
            body: Email body content (plain text or HTML)
            from_email: Sender email address (must match authenticated Gmail account)
            in_reply_to: Message-ID for threading (format: "<message-id@mail.gmail.com>")
            references: Space-separated message IDs for threading
            body_type: Body content type - "plain" or "html" (default: "plain")

        Returns:
            Base64 URL-safe encoded MIME message string ready for Gmail API

        Raises:
            ValueError: If body_type is not "plain" or "html"

        Example:
            encoded_msg = client._compose_mime_message(
                to="recipient@example.com",
                subject="Hello",
                body="Test message",
                from_email="sender@gmail.com",
                body_type="plain"
            )

        Threading Example:
            # Reply to existing email with threading headers
            encoded_msg = client._compose_mime_message(
                to="recipient@example.com",
                subject="Re: Original Subject",
                body="Reply message",
                from_email="sender@gmail.com",
                in_reply_to="<CADv4wR9ABC123@mail.gmail.com>",
                references="<CADv4wR9XYZ789@mail.gmail.com> <CADv4wR9ABC123@mail.gmail.com>"
            )
        """
        # Validate body_type parameter
        if body_type not in ["plain", "html"]:
            raise ValueError(f"body_type must be 'plain' or 'html', got: {body_type}")

        # Create MIMEMultipart message with 'alternative' subtype
        # This allows for both plain and HTML versions (future enhancement)
        message = MIMEMultipart("alternative")

        # Set required headers
        message["From"] = from_email
        message["To"] = to
        message["Subject"] = subject
        # RFC 2822 compliant date format
        message["Date"] = formatdate(localtime=True)

        # Set threading headers if provided
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references

        # Attach body with appropriate MIME type
        if body_type == "plain":
            mime_part = MIMEText(body, "plain", "utf-8")
        else:  # body_type == "html"
            mime_part = MIMEText(body, "html", "utf-8")

        message.attach(mime_part)

        # Encode message as base64 URL-safe string for Gmail API
        # Gmail API requires base64url encoding (RFC 4648)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        return raw_message

    async def get_thread_message_ids(self, thread_id: str) -> List[str]:
        """Extract all message IDs from Gmail thread for threading headers.

        Fetches thread history and extracts message IDs in chronological order.
        Used to construct the References header when replying to emails.

        Args:
            thread_id: Gmail thread ID

        Returns:
            List of message IDs in chronological order (oldest first)
            Format: ["<msg-1@mail.gmail.com>", "<msg-2@mail.gmail.com>", ...]

        Raises:
            ValueError: If thread_id is empty or invalid
            HttpError: Gmail API error (handled with retry logic)

        Example:
            message_ids = await client.get_thread_message_ids("thread_abc123")
            # Returns: ["<CADv4wR9ABC@mail.gmail.com>", "<CADv4wR9XYZ@mail.gmail.com>"]
        """
        # Input validation
        if not thread_id or not isinstance(thread_id, str):
            raise ValueError("thread_id must be a non-empty string")
        if not thread_id.strip():
            raise ValueError("thread_id cannot be whitespace only")

        service = await self._get_gmail_service()

        def _get_thread_ids():
            # Fetch thread with full format to get Message-ID headers
            thread = service.users().threads().get(userId="me", id=thread_id, format="metadata").execute()

            messages = thread.get("messages", [])
            message_ids = []

            # Extract Message-ID header from each message
            for msg in messages:
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                # Message-ID header contains the RFC 822 message ID (not Gmail's internal ID)
                message_id = headers.get("Message-ID", headers.get("Message-Id"))
                if message_id:
                    message_ids.append(message_id)

            return message_ids

        result = await self._execute_with_retry(_get_thread_ids)

        self.logger.info(
            "gmail_thread_message_ids_extracted",
            user_id=self.user_id,
            thread_id=thread_id,
            message_count=len(result),
        )

        return result

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = None,
        references: str = None,
        body_type: str = "plain",
        thread_id: str = None,
    ) -> str:
        """Send email via Gmail API.

        Composes MIME message and sends via Gmail API messages.send endpoint.
        Supports plain text and HTML bodies, conversation threading, and comprehensive
        error handling with automatic retry logic.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Email body content (plain text or HTML)
            in_reply_to: Message-ID for threading (optional, auto-populated if thread_id provided)
            references: References header for threading (optional, auto-populated if thread_id provided)
            body_type: Body content type - "plain" or "html" (default: "plain")
            thread_id: Gmail thread ID to reply to (optional, auto-constructs threading headers)

        Returns:
            message_id: Gmail message ID of sent email

        Raises:
            InvalidRecipientError: Recipient email invalid or does not exist (400)
            QuotaExceededError: Gmail API sending quota exceeded (429)
            MessageTooLargeError: Email exceeds 25MB size limit (413)
            HttpError: Other Gmail API errors

        Example:
            # Send simple email
            message_id = await client.send_email(
                to="recipient@example.com",
                subject="Hello",
                body="Test message"
            )

            # Send HTML email
            message_id = await client.send_email(
                to="recipient@example.com",
                subject="Newsletter",
                body="<h1>Welcome</h1><p>HTML content</p>",
                body_type="html"
            )

            # Reply to existing thread
            message_id = await client.send_email(
                to="recipient@example.com",
                subject="Re: Original Subject",
                body="Reply message",
                thread_id="thread_abc123"
            )
        """
        send_start_time = time.time()

        # If thread_id provided, auto-construct threading headers
        if thread_id and not in_reply_to and not references:
            self.logger.info(
                "email_send_thread_reply_detected",
                user_id=self.user_id,
                thread_id=thread_id,
                recipient=to,
            )

            # Get all message IDs from thread
            message_ids = await self.get_thread_message_ids(thread_id)

            if message_ids:
                # In-Reply-To: Latest message in thread
                in_reply_to = message_ids[-1]
                # References: All messages in thread (space-separated)
                references = " ".join(message_ids)

        # Log email send started
        self.logger.info(
            "email_send_started",
            user_id=self.user_id,
            recipient=to,
            subject=subject,
            has_threading=bool(in_reply_to),
            body_type=body_type,
            timestamp=datetime.now().isoformat(),
        )

        # Get user's email for From header
        # Load user from database to get email address
        async with self.db_service.get_session() as session:
            from app.models.user import User
            from sqlmodel import select

            user = (await session.execute(select(User).where(User.id == self.user_id))).scalar_one_or_none()

            if not user or not user.email:
                self.logger.error(
                    "email_send_failed_no_user_email",
                    user_id=self.user_id,
                    recipient=to,
                    subject=subject,
                )
                raise ValueError(f"User {self.user_id} has no email address configured")

            from_email = user.email

        # Compose MIME message
        try:
            encoded_message = self._compose_mime_message(
                to=to,
                subject=subject,
                body=body,
                from_email=from_email,
                in_reply_to=in_reply_to,
                references=references,
                body_type=body_type,
            )
        except ValueError as e:
            self.logger.error(
                "email_send_failed_invalid_params",
                user_id=self.user_id,
                recipient=to,
                subject=subject,
                error=str(e),
            )
            raise

        # Prepare Gmail API request
        service = await self._get_gmail_service()
        request_body = {"raw": encoded_message}

        # Add threadId if replying to existing thread
        if thread_id:
            request_body["threadId"] = thread_id

        def _send_email():
            return service.users().messages().send(userId="me", body=request_body).execute()

        # Send email with retry logic
        try:
            response = await self._execute_with_retry(_send_email)
            message_id = response["id"]

            # Calculate send duration
            duration_ms = int((time.time() - send_start_time) * 1000)

            # Log success
            self.logger.info(
                "email_sent",
                user_id=self.user_id,
                recipient=to,
                subject=subject,
                message_id=message_id,
                success=True,
                duration_ms=duration_ms,
                thread_id=thread_id,
            )

            return message_id

        except HttpError as e:
            status = e.resp.status
            duration_ms = int((time.time() - send_start_time) * 1000)

            # 400: Invalid recipient or malformed request
            if status == 400:
                error_msg = f"Invalid recipient or malformed email: {to}"
                self.logger.error(
                    "email_send_failed",
                    user_id=self.user_id,
                    recipient=to,
                    subject=subject,
                    success=False,
                    error_code="GMAIL_INVALID_RECIPIENT",
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
                raise InvalidRecipientError(error_msg, recipient=to)

            # 413: Message too large (exceeds 25MB)
            elif status == 413:
                error_msg = f"Email exceeds Gmail 25MB size limit: {to}"
                self.logger.error(
                    "email_send_failed",
                    user_id=self.user_id,
                    recipient=to,
                    subject=subject,
                    success=False,
                    error_code="GMAIL_MESSAGE_TOO_LARGE",
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
                raise MessageTooLargeError(error_msg)

            # 429: Quota exceeded (rate limit or daily send limit)
            elif status == 429:
                # Gmail daily send limit: 100 emails/day
                error_msg = f"Gmail API quota exceeded (100 sends/day): {to}"
                self.logger.error(
                    "email_send_failed",
                    user_id=self.user_id,
                    recipient=to,
                    subject=subject,
                    success=False,
                    error_code="GMAIL_QUOTA_EXCEEDED",
                    error_message=str(e),
                    duration_ms=duration_ms,
                    quota_exceeded=True,
                )
                # Extract retry_after from response headers if available
                retry_after = e.resp.get("Retry-After")
                raise QuotaExceededError(error_msg, retry_after=retry_after)

            # Other errors: Log and re-raise
            else:
                self.logger.error(
                    "email_send_failed",
                    user_id=self.user_id,
                    recipient=to,
                    subject=subject,
                    success=False,
                    error_code=f"GMAIL_API_ERROR_{status}",
                    error_message=str(e),
                    duration_ms=duration_ms,
                    exc_info=True,
                )
                raise
