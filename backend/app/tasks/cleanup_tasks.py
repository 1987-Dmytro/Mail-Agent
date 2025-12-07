"""Cleanup tasks for maintaining vector database retention policy.

This module provides Celery periodic tasks for cleaning up old email embeddings
from ChromaDB according to the 90-day retention policy.
"""

import structlog
from sqlmodel import select

from app.celery import celery_app
from app.models.user import User
from app.services.database import database_service
from app.services.email_indexing import EmailIndexingService


logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_old_vector_embeddings")
def cleanup_old_vector_embeddings():
    """Cleanup emails older than 90 days from ChromaDB for all active users.

    This task runs daily at 3:00 AM UTC via Celery Beat to enforce 90-day
    retention policy for vector embeddings (2025 RAG best practice).

    Reduces:
    - Storage costs (fewer embeddings to store)
    - Query latency (smaller vector DB = faster search)
    - Memory usage (less data to load)

    Workflow:
    1. Query all active users from database
    2. For each user, call EmailIndexingService.cleanup_old_emails(days=90)
    3. Log cleanup statistics

    Example log output:
        cleanup_vector_embeddings_started: user_count=5
        cleanup_completed_for_user: user_id=1, deleted_count=234
        cleanup_completed_for_user: user_id=2, deleted_count=0
        cleanup_all_users_completed: total_deleted=450, users_processed=5
    """
    logger.info("cleanup_vector_embeddings_started")

    total_deleted = 0
    users_processed = 0

    try:
        # Get all active users
        with database_service.session() as session:
            result = session.execute(select(User))
            users = result.scalars().all()

        logger.info("cleanup_found_users", user_count=len(users))

        # Cleanup old embeddings for each user
        for user in users:
            try:
                # Initialize EmailIndexingService for this user
                indexing_service = EmailIndexingService(user_id=user.id)

                # Run cleanup (synchronous wrapper for async method)
                import asyncio
                deleted_count = asyncio.run(indexing_service.cleanup_old_emails(days=90))

                total_deleted += deleted_count
                users_processed += 1

                logger.info(
                    "cleanup_completed_for_user",
                    user_id=user.id,
                    deleted_count=deleted_count
                )

            except Exception as e:
                logger.error(
                    "cleanup_failed_for_user",
                    user_id=user.id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                # Continue processing other users even if one fails
                continue

        logger.info(
            "cleanup_all_users_completed",
            total_deleted=total_deleted,
            users_processed=users_processed
        )

        return {
            "total_deleted": total_deleted,
            "users_processed": users_processed
        }

    except Exception as e:
        logger.error(
            "cleanup_task_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
