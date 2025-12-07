#!/usr/bin/env python3
"""
Reindex existing emails 252-261 that were received before incremental indexing was enabled.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.models.email_processing_queue import EmailProcessingQueue
from app.services.database import database_service
from app.tasks.indexing_tasks import index_new_email_background


async def main():
    """Reindex emails 252-261 for user_id=3."""
    print("Starting reindexing of emails 252-261...")

    async with database_service.async_session() as session:
        # Get emails 252-261
        result = await session.execute(
            select(EmailProcessingQueue)
            .where(
                EmailProcessingQueue.id >= 252,
                EmailProcessingQueue.id <= 261,
                EmailProcessingQueue.user_id == 3
            )
            .order_by(EmailProcessingQueue.id)
        )
        emails = result.scalars().all()

        print(f"Found {len(emails)} emails to reindex")

        # Queue indexing tasks
        queued_count = 0
        for email in emails:
            try:
                # Queue background task
                index_new_email_background.delay(
                    user_id=email.user_id,
                    message_id=email.gmail_message_id
                )
                print(f"✅ Queued: Email {email.id} - {email.subject}")
                queued_count += 1
            except Exception as e:
                print(f"❌ Failed to queue email {email.id}: {e}")

        print(f"\n✅ Reindexing complete: {queued_count}/{len(emails)} emails queued")
        print("Tasks are running in background. Check celery-worker logs for progress.")


if __name__ == "__main__":
    asyncio.run(main())
