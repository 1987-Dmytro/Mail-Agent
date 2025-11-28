"""E2E tests for real Telegram Bot API integration.

CRITICAL: These tests make REAL API calls to Telegram.
- Requires valid Telegram bot token
- Sends real messages to test chat
- May trigger rate limits if run too frequently

Run only before releases or when explicitly needed.

Setup:
    1. Set TELEGRAM_BOT_TOKEN environment variable
    2. Set TELEGRAM_TEST_CHAT_ID (your test Telegram user ID)
    3. Start chat with bot and send /start
    4. Run: pytest tests/e2e/test_telegram_real_api.py -v -m e2e

These tests verify:
    - Real Telegram Bot API connectivity
    - Message sending works
    - Inline keyboards render correctly
    - Callback queries can be handled
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, UTC

from app.core.telegram_bot import TelegramBotClient


pytestmark = pytest.mark.e2e


@pytest.mark.skipif(
    not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_TEST_CHAT_ID"),
    reason="TELEGRAM_BOT_TOKEN or TELEGRAM_TEST_CHAT_ID not set. Set them to enable real Telegram API E2E tests.",
)
class TestTelegramRealAPI:
    """E2E tests with REAL Telegram Bot API."""

    @pytest_asyncio.fixture
    async def real_telegram_client(self):
        """Create real Telegram bot client with test bot credentials.

        Expects:
        - TELEGRAM_BOT_TOKEN: Your test bot token from @BotFather
        - TELEGRAM_TEST_CHAT_ID: Your personal Telegram user ID (for receiving test messages)
        """
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

        client = TelegramBotClient(bot_token=bot_token)
        await client.initialize()

        yield client

        # Cleanup
        await client.stop()

    @pytest.mark.asyncio
    async def test_telegram_send_simple_message_e2e(self, real_telegram_client: TelegramBotClient):
        """E2E: Send a simple text message to real Telegram chat.

        This test verifies:
        - Real Telegram Bot API connectivity
        - Bot token is valid
        - Message sending succeeds
        - Message ID returned

        AC Coverage: Epic 2 - Telegram notifications
        """
        test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
        timestamp = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        test_message = f"🧪 E2E Test Message\n\nTimestamp: {timestamp}\n\nThis is an automated E2E test from Mail Agent backend."

        # Send message via real Telegram API
        message_id = await real_telegram_client.send_message(
            telegram_id=test_chat_id,
            text=test_message,
        )

        # Verify message ID returned
        assert message_id is not None, "Message ID is None"
        assert isinstance(message_id, (str, int)), f"Message ID has wrong type: {type(message_id)}"

        print(f"✅ Sent real Telegram message (ID: {message_id}) to chat {test_chat_id}")
        print(f"📱 Check your Telegram app - you should see the test message!")

    @pytest.mark.asyncio
    async def test_telegram_send_message_with_buttons_e2e(self, real_telegram_client: TelegramBotClient):
        """E2E: Send message with inline keyboard buttons.

        This test verifies:
        - Inline keyboard rendering
        - Buttons appear in Telegram app
        - Button callback data structure

        AC Coverage: Epic 2 - Approval buttons

        Note: This test sends a message with buttons but doesn't simulate button clicks.
        Manual verification: Check buttons appear correctly in Telegram app.
        """
        test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
        timestamp = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')

        test_message = f"""📬 E2E Test: Email Sorting Proposal

**From:** test@example.com
**Subject:** Test Email for E2E

**AI Suggestion:** Government folder
**Reasoning:** Testing inline keyboard buttons

Timestamp: {timestamp}

⚠️ This is a test message. Do NOT click buttons unless testing callbacks."""

        # Create inline keyboard with test buttons
        buttons = [
            [
                {"text": "✅ Approve", "callback_data": "approve_test_123"},
                {"text": "📁 Change Folder", "callback_data": "change_folder_test_123"},
            ],
            [
                {"text": "❌ Reject", "callback_data": "reject_test_123"},
            ],
        ]

        # Send message with buttons via real Telegram API
        message_id = await real_telegram_client.send_message_with_buttons(
            telegram_id=test_chat_id,
            text=test_message,
            buttons=buttons,
        )

        # Verify message ID returned
        assert message_id is not None
        print(f"✅ Sent Telegram message with inline keyboard (ID: {message_id})")
        print(f"📱 Check your Telegram app - you should see 3 buttons:")
        print(f"   - ✅ Approve")
        print(f"   - 📁 Change Folder")
        print(f"   - ❌ Reject")

    @pytest.mark.asyncio
    async def test_telegram_edit_message_e2e(self, real_telegram_client: TelegramBotClient):
        """E2E: Edit an existing message.

        This test verifies:
        - Message editing works
        - Text update reflects in Telegram app

        AC Coverage: Epic 2 - Confirmation messages (edit original proposal)
        """
        test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
        timestamp = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')

        # Step 1: Send original message
        original_text = f"🧪 E2E Test: Original Message\n\nTimestamp: {timestamp}\n\nThis message will be edited..."

        message_id = await real_telegram_client.send_message(
            telegram_id=test_chat_id,
            text=original_text,
        )

        print(f"✅ Sent original message (ID: {message_id})")

        # Step 2: Edit the message
        edited_text = f"✏️ E2E Test: EDITED Message\n\nTimestamp: {timestamp}\n\n✅ This message was successfully edited by E2E test!"

        await real_telegram_client.edit_message_text(
            telegram_id=test_chat_id,
            message_id=message_id,
            text=edited_text,
        )

        print(f"✅ Edited message (ID: {message_id})")
        print(f"📱 Check your Telegram app - message should show 'EDITED' text")

    @pytest.mark.asyncio
    async def test_telegram_html_formatting_e2e(self, real_telegram_client: TelegramBotClient):
        """E2E: Send message with HTML formatting.

        This test verifies:
        - HTML parse mode works
        - Bold, italic, code formatting renders correctly

        AC Coverage: Epic 2 - Message formatting
        """
        test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
        timestamp = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')

        # Message with HTML formatting
        formatted_message = f"""<b>🧪 E2E Test: HTML Formatting</b>

<b>Bold text</b>
<i>Italic text</i>
<code>Code text</code>
<pre>Preformatted block</pre>

<b>From:</b> <code>sender@example.com</code>
<b>Subject:</b> Testing HTML formatting

Timestamp: {timestamp}"""

        message_id = await real_telegram_client.send_message(
            telegram_id=test_chat_id,
            text=formatted_message,
            parse_mode="HTML",
        )

        print(f"✅ Sent message with HTML formatting (ID: {message_id})")
        print(f"📱 Check your Telegram app - formatting should be applied:")
        print(f"   - Bold text should be bold")
        print(f"   - Italic text should be italic")
        print(f"   - Code should be monospace")
