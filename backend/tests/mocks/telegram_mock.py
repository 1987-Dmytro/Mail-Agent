"""Mock Telegram Bot API client for integration testing.

This mock provides deterministic responses for testing Telegram bot operations
without making real API calls to Telegram Bot API.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC


class TelegramAPIError(Exception):
    """Mock Telegram API error for testing error scenarios."""
    pass


class MockTelegramBot:
    """Mock implementation of Telegram Bot API client for testing.

    Tracks all Telegram operations (send message, answer callback, buttons)
    for test assertions and simulates user interactions.
    """

    def __init__(self):
        """Initialize mock with empty tracking."""
        self.sent_messages: List[Dict[str, Any]] = []
        self.callback_queries_answered: List[str] = []
        self.simulated_callbacks: List[Dict[str, Any]] = []
        self._message_id_counter = 1000
        self._simulate_network_error = False
        self._response_delay: float = 0.0
        self._failure_exception: Exception | None = None
        self._failure_count: int = 0
        self._current_call_count: int = 0

    def enable_network_error(self):
        """Configure mock to simulate network errors on next API call."""
        self._simulate_network_error = True

    def set_response_delay(self, delay: float):
        """Set artificial delay for API responses to simulate latency.

        Args:
            delay: Delay in seconds to add before returning responses
        """
        self._response_delay = delay

    def set_failure_mode(self, exception: Exception, fail_count: int):
        """Configure mock to raise exceptions for testing error handling.

        Args:
            exception: Exception to raise on API calls
            fail_count: Number of calls that should fail before succeeding
        """
        self._failure_exception = exception
        self._failure_count = fail_count
        self._current_call_count = 0

    async def send_message(
        self,
        telegram_id: str,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        user_id: int = None  # Matches real TelegramBotClient signature
    ) -> str:
        """Mock send_message operation.

        Args:
            telegram_id: Telegram user ID (matches real TelegramBotClient API)
            text: Message text content
            reply_markup: Inline keyboard markup (optional)
            user_id: Optional database user_id (ignored in mock)

        Returns:
            str: Mock message ID

        Raises:
            TelegramAPIError: If network error simulation is enabled
        """
        # Handle failure mode (newer test pattern)
        self._current_call_count += 1
        if self._failure_exception and self._current_call_count <= self._failure_count:
            raise self._failure_exception

        # Handle old network error pattern
        if self._simulate_network_error:
            self._simulate_network_error = False
            raise TelegramAPIError("Network timeout")

        # Add artificial delay if configured
        if self._response_delay > 0:
            import asyncio
            await asyncio.sleep(self._response_delay)

        # Generate unique message ID
        message_id = f"msg_{self._message_id_counter}"
        self._message_id_counter += 1

        # Track sent message with full details (store as chat_id for internal consistency)
        self.sent_messages.append({
            "message_id": message_id,
            "chat_id": telegram_id,  # Store as chat_id for internal tracking methods
            "text": text,
            "reply_markup": reply_markup,
            "timestamp": datetime.now(UTC),
            "buttons": self._extract_buttons(reply_markup) if reply_markup else []
        })

        return message_id

    async def send_message_with_buttons(
        self,
        telegram_id: str,
        text: str,
        buttons: list[list[Any]],
        user_id: int = None  # Matches real TelegramBotClient signature
    ) -> str:
        """Mock send_message_with_buttons operation (alias for send_message with inline keyboard).

        Args:
            telegram_id: Telegram user ID
            text: Message text content
            buttons: Button layout (list of rows, each row is list of buttons or InlineKeyboardButton objects)
            user_id: Optional database user_id (ignored in mock)

        Returns:
            str: Mock message ID
        """
        # Convert InlineKeyboardButton objects to dict format if needed
        button_dicts = []
        for row in buttons:
            row_dicts = []
            for button in row:
                if hasattr(button, 'text') and hasattr(button, 'callback_data'):
                    # InlineKeyboardButton object
                    row_dicts.append({
                        "text": button.text,
                        "callback_data": button.callback_data
                    })
                elif isinstance(button, dict):
                    # Already a dict
                    row_dicts.append(button)
                else:
                    # Unknown format, convert to string
                    row_dicts.append({"text": str(button), "callback_data": str(button)})
            button_dicts.append(row_dicts)

        # Convert buttons to reply_markup format
        reply_markup = {
            "inline_keyboard": button_dicts
        } if button_dicts else None

        # Call send_message with reply_markup
        return await self.send_message(
            telegram_id=telegram_id,
            text=text,
            reply_markup=reply_markup,
            user_id=user_id
        )

    async def edit_message_text(
        self,
        telegram_id: str,
        message_id: str,
        text: str,
    ) -> bool:
        """Mock edit_message_text operation.

        Args:
            telegram_id: Telegram user ID (matches real TelegramBotClient API)
            message_id: Message ID to edit
            text: New message text

        Returns:
            bool: True if successful
        """
        # Find and update the message
        for msg in self.sent_messages:
            if msg["message_id"] == message_id and msg["chat_id"] == telegram_id:
                msg["text"] = text
                return True
        return False

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None
    ) -> bool:
        """Mock answer_callback_query operation.

        Args:
            callback_query_id: Callback query ID to acknowledge
            text: Optional text to show in popup

        Returns:
            bool: True if successful
        """
        self.callback_queries_answered.append(callback_query_id)
        return True

    def simulate_user_callback(
        self,
        callback_data: str,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Simulate user clicking a button in Telegram.

        Args:
            callback_data: Callback data from button (e.g., "approve_123")
            message_id: Message ID containing the button (optional)

        Returns:
            dict: Mock callback query object
        """
        callback_query = {
            "id": f"cbq_{len(self.simulated_callbacks) + 1}",
            "from": {
                "id": 123456789,
                "username": "testuser"
            },
            "message": {
                "message_id": message_id or "msg_1000",
                "chat": {"id": 123456789}
            },
            "data": callback_data,
            "timestamp": datetime.now(UTC)
        }

        self.simulated_callbacks.append(callback_query)
        return callback_query

    def get_last_message(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent message sent to a specific chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            dict or None: Message details if found
        """
        messages = [m for m in self.sent_messages if m["chat_id"] == chat_id]
        return messages[-1] if messages else None

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message details by message ID.

        Args:
            message_id: Message ID to retrieve

        Returns:
            dict or None: Message details if found
        """
        for msg in self.sent_messages:
            if msg["message_id"] == message_id:
                return msg
        return None

    def get_messages_for_chat(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get all messages sent to a specific chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            list: List of message dictionaries
        """
        return [m for m in self.sent_messages if m["chat_id"] == chat_id]

    def count_messages(self, chat_id: Optional[str] = None) -> int:
        """Count total messages sent (optionally filtered by chat).

        Args:
            chat_id: Optional chat ID to filter by

        Returns:
            int: Number of messages
        """
        if chat_id:
            return len([m for m in self.sent_messages if m["chat_id"] == chat_id])
        return len(self.sent_messages)

    def _extract_buttons(self, reply_markup: Dict[str, Any]) -> List[List[str]]:
        """Extract button labels from inline keyboard markup.

        Args:
            reply_markup: Telegram inline keyboard markup

        Returns:
            list: Nested list of button labels (rows of buttons)
        """
        if not reply_markup or "inline_keyboard" not in reply_markup:
            return []

        buttons = []
        for row in reply_markup["inline_keyboard"]:
            button_row = [btn.get("text", "") for btn in row]
            buttons.append(button_row)

        return buttons

    def verify_message_contains(
        self,
        chat_id: str,
        text_substring: str
    ) -> bool:
        """Verify that at least one message to chat contains text.

        Args:
            chat_id: Telegram chat ID
            text_substring: Text to search for (case-sensitive)

        Returns:
            bool: True if any message contains the substring
        """
        for msg in self.sent_messages:
            if msg["chat_id"] == chat_id and text_substring in msg["text"]:
                return True
        return False

    def verify_button_exists(
        self,
        message_id: str,
        button_text: str
    ) -> bool:
        """Verify that a message contains a specific button.

        Args:
            message_id: Message ID to check
            button_text: Button text to search for (supports partial matching)

        Returns:
            bool: True if button exists in message (text is substring of any button)
        """
        msg = self.get_message_by_id(message_id)
        if not msg or not msg.get("buttons"):
            return False

        # Flatten button rows and check if button_text is in any button text
        all_buttons = [btn for row in msg["buttons"] for btn in row]
        return any(button_text in btn for btn in all_buttons)

    def reset(self):
        """Clear all tracking data."""
        self.sent_messages.clear()
        self.callback_queries_answered.clear()
        self.simulated_callbacks.clear()
        self._message_id_counter = 1000
        self._simulate_network_error = False
