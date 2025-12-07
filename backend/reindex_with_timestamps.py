#!/usr/bin/env python3
"""
Re-index all emails to add timestamp metadata to ChromaDB.

This script deletes existing email_embeddings collection and re-indexes
all emails from the last 90 days with the new metadata schema including timestamps.
"""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.email_indexing import EmailIndexingService
from app.services.gmail import GmailClient
from app.database import DatabaseService
from app.models.user import User
from sqlalchemy import select

async def reindex_all_emails():
    """Re-index all emails for all users with new timestamp metadata."""

    print("=" * 80)
    print("RE-INDEXING ALL EMAILS WITH TIMESTAMP METADATA")
    print("=" * 80)
    print()

    db_service = DatabaseService()

    # Get all users with Gmail connected
    async with db_service.async_session() as session:
        result = await session.execute(
            select(User).where(User.gmail_credentials != None)
        )
        users = result.scalars().all()

    print(f"Found {len(users)} users with Gmail connected")
    print()

    for user in users:
        print(f"📧 Processing user {user.id}: {user.email}")
        print("-" * 80)

        try:
            # Initialize Gmail client
            gmail_client = GmailClient(
                credentials_json=user.gmail_credentials,
                user_email=user.email
            )

            # Initialize indexing service
            indexing_service = EmailIndexingService(
                user_id=user.id,
                gmail_client=gmail_client,
                db_service=db_service
            )

            # Delete old collection for this user (if exists)
            # This removes old embeddings without timestamp metadata
            print(f"   Clearing old embeddings from ChromaDB...")
            try:
                # Get all existing embeddings for this user
                collection = indexing_service.vector_db_client.client.get_collection("email_embeddings")

                # Delete emails for this user
                # ChromaDB doesn't support delete by filter, so we query first
                existing = collection.get(
                    where={"user_id": str(user.id)},
                    limit=10000  # Max batch size
                )

                if existing['ids']:
                    collection.delete(ids=existing['ids'])
                    print(f"   ✅ Deleted {len(existing['ids'])} old embeddings")
                else:
                    print(f"   ℹ️  No existing embeddings found")

            except Exception as e:
                print(f"   ⚠️  Could not delete old embeddings: {e}")

            # Re-index all emails (90 days) with new metadata schema
            print(f"   Re-indexing emails from last 90 days...")
            progress = await indexing_service.index_emails(days_back=90)

            print(f"   ✅ Indexed {progress.total_emails} emails")
            print(f"   Status: {progress.status}")
            print()

        except Exception as e:
            print(f"   ❌ Error processing user {user.id}: {e}")
            import traceback
            traceback.print_exc()
            print()
            continue

    print("=" * 80)
    print("✅ RE-INDEXING COMPLETE")
    print("=" * 80)
    print()
    print("All emails now have timestamp metadata for temporal filtering!")
    print()

if __name__ == "__main__":
    asyncio.run(reindex_all_emails())
