"""Test script to verify sender_history retrieval from ChromaDB."""

import asyncio
import sys
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.context_retrieval import ContextRetrievalService
from app.core.config import settings


async def test_sender_history():
    """Test sender history retrieval for hordieenko.dmytro@keemail.me."""

    print("\n" + "="*80)
    print("Testing Sender History Retrieval")
    print("="*80 + "\n")

    # Initialize service
    service = ContextRetrievalService(user_id=1)

    # Test parameters
    sender = "hordieenko.dmytro@keemail.me"

    print(f"Retrieving ALL emails from sender: {sender}")
    print(f"Time window: Last 90 days")
    print(f"Max emails: 50")
    print("-" * 80 + "\n")

    try:
        # Call the new _get_sender_history method
        sender_history, count = await service._get_sender_history(
            sender=sender,
            user_id=1,
            days=90,
            max_emails=50
        )

        print(f"✅ Retrieved {count} emails from sender\n")

        if sender_history:
            print("Email Details:")
            print("-" * 80)
            for i, email in enumerate(sender_history, 1):
                print(f"\n{i}. Message ID: {email['message_id']}")
                print(f"   Subject: {email['subject']}")
                print(f"   Date: {email['date']}")
                print(f"   Thread ID: {email['thread_id']}")
                print(f"   Body preview: {email['body'][:150]}...")
        else:
            print("⚠️  No emails found from this sender")
            print("\nPossible reasons:")
            print("1. Emails not yet indexed in ChromaDB")
            print("2. Sender email doesn't match exactly")
            print("3. Emails outside 90-day window")

        print("\n" + "="*80)
        print("Test Complete")
        print("="*80)

        return sender_history, count

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], 0


if __name__ == "__main__":
    asyncio.run(test_sender_history())
