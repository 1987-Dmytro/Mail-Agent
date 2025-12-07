#!/usr/bin/env python3
"""
Quick script to manually delete draft message 2264 from Telegram.
This is a one-time cleanup for email 261 that was processed with old code.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.telegram_bot import TelegramBotClient


async def main():
    """Delete draft message 2264."""
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Your Telegram ID from logs
    telegram_id = "1658562597"
    message_id = "2264"

    print(f"Deleting message {message_id} from chat {telegram_id}...")

    success = await telegram_bot.delete_message(
        telegram_id=telegram_id,
        message_id=message_id
    )

    if success:
        print("✅ Message deleted successfully!")
    else:
        print("❌ Failed to delete message")


if __name__ == "__main__":
    asyncio.run(main())
