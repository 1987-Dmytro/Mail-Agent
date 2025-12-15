"""Indexing Recovery Service - Sync Pinecone state with Database.

This service handles edge cases where indexing completed in Pinecone
but the database IndexingProgress record wasn't updated (e.g., due to
worker crashes, deployments, or DB connection issues).
"""
import structlog
from datetime import datetime, UTC
from sqlmodel import select

from app.core.vector_db_pinecone import PineconeVectorDBClient
from app.models.indexing_progress import IndexingProgress, IndexingStatus
from app.services.database import database_service

logger = structlog.get_logger(__name__)


class IndexingRecoveryService:
    """Service to recover and sync indexing state from Pinecone."""

    def __init__(self, pinecone_client: PineconeVectorDBClient):
        """Initialize recovery service.

        Args:
            pinecone_client: Pinecone client to check vector counts
        """
        self.pinecone_client = pinecone_client
        self.logger = logger.bind(service="indexing_recovery")

    async def check_and_recover_user(self, user_id: int) -> bool:
        """Check if user's indexing is complete in Pinecone and sync DB.

        This function:
        1. Gets vector count from Pinecone for user
        2. Checks IndexingProgress in database
        3. If vectors exist but DB status is not COMPLETED, syncs the state

        Args:
            user_id: User ID to check

        Returns:
            True if recovery was performed, False if no action needed
        """
        self.logger.info("checking_indexing_recovery", user_id=user_id)

        # Get Pinecone stats for user's namespace
        try:
            index = self.pinecone_client.client.Index(self.pinecone_client.index_name)
            stats = index.describe_index_stats()
            namespace = self.pinecone_client.DEFAULT_NAMESPACE

            namespaces = stats.get('namespaces', {})
            if namespace not in namespaces:
                self.logger.info(
                    "no_vectors_in_pinecone",
                    user_id=user_id,
                    namespace=namespace
                )
                return False

            vector_count = namespaces[namespace].get('vector_count', 0)

            if vector_count == 0:
                self.logger.info("no_vectors_to_recover", user_id=user_id)
                return False

            self.logger.info(
                "pinecone_vectors_found",
                user_id=user_id,
                vector_count=vector_count
            )

        except Exception as e:
            self.logger.error(
                "failed_to_check_pinecone",
                user_id=user_id,
                error=str(e)
            )
            return False

        # Check database IndexingProgress
        async with database_service.async_session() as session:
            result = await session.execute(
                select(IndexingProgress).where(IndexingProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()

            # Case 1: No record exists but vectors in Pinecone - create COMPLETED record
            if not progress:
                self.logger.warning(
                    "missing_indexing_record_creating",
                    user_id=user_id,
                    vector_count=vector_count
                )

                progress = IndexingProgress(
                    user_id=user_id,
                    status=IndexingStatus.COMPLETED,
                    total_emails=vector_count,
                    processed_count=vector_count,
                    completed_at=datetime.now(UTC),
                    last_processed_message_id=None
                )
                session.add(progress)
                await session.commit()

                self.logger.info(
                    "indexing_record_recovered",
                    user_id=user_id,
                    vector_count=vector_count,
                    action="created_completed_record"
                )
                return True

            # Case 2: Record exists but status is not COMPLETED
            if progress.status != IndexingStatus.COMPLETED:
                # Check if Pinecone vectors match or exceed total_emails
                if vector_count >= progress.total_emails:
                    self.logger.warning(
                        "indexing_complete_in_pinecone_but_db_not_updated",
                        user_id=user_id,
                        db_status=progress.status.value,
                        db_processed=progress.processed_count,
                        db_total=progress.total_emails,
                        pinecone_vectors=vector_count
                    )

                    # Sync DB to match Pinecone reality
                    progress.status = IndexingStatus.COMPLETED
                    progress.processed_count = vector_count
                    progress.total_emails = max(progress.total_emails, vector_count)
                    progress.completed_at = datetime.now(UTC)

                    await session.commit()

                    self.logger.info(
                        "indexing_record_recovered",
                        user_id=user_id,
                        vector_count=vector_count,
                        action="updated_to_completed"
                    )
                    return True
                else:
                    self.logger.info(
                        "indexing_in_progress_correct",
                        user_id=user_id,
                        db_processed=progress.processed_count,
                        db_total=progress.total_emails,
                        pinecone_vectors=vector_count
                    )
                    return False

            # Case 3: Already COMPLETED - no action needed
            self.logger.info(
                "indexing_already_completed",
                user_id=user_id,
                vector_count=vector_count
            )
            return False
