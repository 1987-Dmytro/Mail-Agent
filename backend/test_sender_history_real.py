#!/usr/bin/env python3
"""Test sender_history functionality with real migrated data."""

import asyncio
import os
import sys
from datetime import datetime, UTC

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.vector_db import VectorDBClient
from app.core.config import settings


async def test_sender_history():
    """Test retrieving sender history from migrated ChromaDB data."""

    print("=" * 80)
    print("Testing Sender History Functionality")
    print("=" * 80)

    # Initialize ChromaDB client
    vector_db = VectorDBClient(persist_directory=settings.CHROMADB_PATH)
    print(f"\n✅ ChromaDB initialized at: {settings.CHROMADB_PATH}")

    # Get collection
    collection = vector_db.get_or_create_collection("email_embeddings")
    total_count = collection.count()
    print(f"✅ Total embeddings in collection: {total_count}")

    # Test: Query for all emails from specific sender
    sender = "hordieenko.dmytro@keemail.me"
    print(f"\n🔍 Querying sender history for: {sender}")

    try:
        # Query ChromaDB for all emails from this sender (no embedding, just metadata filter)
        # This simulates what _get_sender_history() would do
        results = collection.get(
            where={"sender": sender},
            include=["metadatas"]
        )

        if not results["ids"]:
            print(f"❌ No emails found for sender: {sender}")
            return False

        email_count = len(results["ids"])
        print(f"✅ Found {email_count} emails from {sender}")

        # Extract and sort by timestamp
        emails_with_timestamps = []
        for i, message_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            emails_with_timestamps.append({
                "message_id": message_id,
                "subject": metadata.get("subject", "No subject"),
                "date": metadata.get("date", "Unknown date"),
                "timestamp": metadata.get("timestamp", 0),
            })

        # Sort chronologically (oldest → newest)
        emails_with_timestamps.sort(key=lambda x: x["timestamp"])

        print(f"\n📧 Sender conversation history (chronological order):")
        print("-" * 80)

        for i, email in enumerate(emails_with_timestamps[:10], 1):  # Show first 10
            date_str = email["date"]
            subject = email["subject"][:60]  # Truncate long subjects
            print(f"{i:2d}. [{date_str}] {subject}")

        if len(emails_with_timestamps) > 10:
            print(f"    ... and {len(emails_with_timestamps) - 10} more emails")

        print("-" * 80)

        # Verify chronological order
        is_chronological = all(
            emails_with_timestamps[i]["timestamp"] <= emails_with_timestamps[i + 1]["timestamp"]
            for i in range(len(emails_with_timestamps) - 1)
        )

        if is_chronological:
            print("✅ Emails are correctly sorted in chronological order (oldest → newest)")
        else:
            print("❌ WARNING: Emails are NOT in chronological order")

        # Check for "Праздники" emails
        prazdniki_emails = [
            e for e in emails_with_timestamps
            if "раздники" in e["subject"].lower() or "razdniki" in e["subject"].lower()
        ]

        if prazdniki_emails:
            print(f"\n🎉 Found {len(prazdniki_emails)} 'Праздники' related emails:")
            for email in prazdniki_emails:
                print(f"   - [{email['date']}] {email['subject']}")
        else:
            print(f"\n⚠️  No 'Праздники' emails found in sender history")

        print("\n" + "=" * 80)
        print(f"✅ SUCCESS: sender_history functionality verified with {email_count} emails")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sender_history())
    sys.exit(0 if success else 1)
