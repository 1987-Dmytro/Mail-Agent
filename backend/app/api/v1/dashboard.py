"""Dashboard endpoints for displaying user statistics and system status."""

from datetime import datetime, timedelta, UTC
from typing import Dict, Any
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.api.v1.auth import get_current_user
from app.api.deps import get_async_db
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.models.indexing_progress import IndexingProgress, IndexingStatus
from app.core.vector_db import VectorDBClient
import structlog


router = APIRouter()
logger = structlog.get_logger(__name__)


class DashboardStatsResponse(BaseModel):
    """Response schema for dashboard statistics."""

    total_processed: int = Field(0, description="Total emails processed")
    pending_approval: int = Field(0, description="Emails awaiting approval")
    auto_sorted: int = Field(0, description="Emails automatically sorted")
    responses_sent: int = Field(0, description="AI-generated responses sent")
    gmail_connected: bool = Field(False, description="Gmail connection status")
    telegram_connected: bool = Field(False, description="Telegram connection status")

    # Vector database status
    vector_db_connected: bool = Field(False, description="ChromaDB vector database connection status")

    # RAG indexing progress
    indexing_in_progress: bool = Field(False, description="Whether email indexing is currently running")
    indexing_total_emails: int = Field(0, description="Total emails to index")
    indexing_processed_count: int = Field(0, description="Number of emails indexed so far")
    indexing_progress_percent: int = Field(0, description="Indexing progress percentage (0-100)")
    indexing_status: str | None = Field(None, description="Indexing status: in_progress/completed/failed/paused")
    indexing_error: str | None = Field(None, description="Error message if indexing failed")


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get dashboard statistics for the authenticated user.

    This endpoint provides real-time dashboard metrics:
    - total_processed: Count of all processed emails (any status)
    - pending_approval: Count of emails waiting for user approval
    - auto_sorted: Count of emails that were automatically sorted
    - responses_sent: Count of emails where AI response was sent
    - gmail_connected: Boolean indicating if Gmail is connected
    - telegram_connected: Boolean indicating if Telegram is linked

    Args:
        current_user: Authenticated user from JWT token
        db: Async database session

    Returns:
        DashboardStatsResponse: Dashboard statistics

    Example Request:
        GET /api/v1/dashboard/stats
        Headers:
            Authorization: Bearer {jwt_token}

    Example Response:
        {
            "total_processed": 150,
            "pending_approval": 5,
            "auto_sorted": 120,
            "responses_sent": 80,
            "gmail_connected": true,
            "telegram_connected": true
        }
    """
    try:
        # Query total processed emails (only completed ones)
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "completed"
            )
        )
        total_processed = result.scalar() or 0

        # Query pending approval (status = 'awaiting_approval')
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "awaiting_approval"
            )
        )
        pending_approval = result.scalar() or 0

        # Query auto-sorted emails (status = 'completed' and user didn't change folder)
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "completed"
            )
        )
        auto_sorted = result.scalar() or 0

        # Query responses sent (emails where classification = 'needs_response' and draft_response exists)
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.classification == "needs_response",
                EmailProcessingQueue.draft_response.isnot(None)
            )
        )
        responses_sent = result.scalar() or 0

        # Check Gmail connection (gmail_oauth_token exists)
        gmail_connected = current_user.gmail_oauth_token is not None

        # Check Telegram connection (telegram_id exists)
        telegram_connected = current_user.telegram_id is not None

        # Check ChromaDB vector database connection
        vector_db_connected = False
        try:
            from app.core.config import settings
            vector_db_client = VectorDBClient(
                persist_directory=settings.CHROMADB_PATH
            )
            vector_db_connected = vector_db_client.health_check()
            logger.debug(
                "vector_db_health_check",
                user_id=current_user.id,
                connected=vector_db_connected,
            )
        except Exception as e:
            logger.warning(
                "vector_db_health_check_failed",
                user_id=current_user.id,
                error=str(e),
            )
            vector_db_connected = False

        # Fetch indexing progress
        result = await db.execute(
            select(IndexingProgress).where(IndexingProgress.user_id == current_user.id)
        )
        indexing = result.scalar_one_or_none()

        # Calculate indexing metrics
        indexing_in_progress = False
        indexing_total_emails = 0
        indexing_processed_count = 0
        indexing_progress_percent = 0
        indexing_status = None
        indexing_error = None

        if indexing:
            indexing_status = indexing.status.value
            indexing_total_emails = indexing.total_emails
            indexing_processed_count = indexing.processed_count
            indexing_in_progress = indexing.status == IndexingStatus.IN_PROGRESS
            indexing_error = indexing.error_message

            # Calculate progress percentage
            if indexing_total_emails > 0:
                indexing_progress_percent = int(
                    (indexing_processed_count / indexing_total_emails) * 100
                )

            # Auto-resume interrupted indexing (e.g., after worker restart)
            if indexing.status == IndexingStatus.IN_PROGRESS and indexing_processed_count < indexing_total_emails:
                # Check if indexing was interrupted (no active Celery task)
                # We can't easily check Celery active tasks here, but resume_user_indexing
                # has built-in protection against duplicates via database constraints
                try:
                    from app.tasks.indexing_tasks import resume_user_indexing
                    resume_user_indexing.delay(user_id=current_user.id)
                    logger.info(
                        "indexing_auto_resumed_from_dashboard",
                        user_id=current_user.id,
                        processed=indexing_processed_count,
                        total=indexing_total_emails,
                        reason="interrupted_indexing_detected",
                    )
                except Exception as resume_error:
                    logger.warning(
                        "indexing_auto_resume_failed",
                        user_id=current_user.id,
                        error=str(resume_error),
                    )

            # Auto-retry failed indexing (only once - don't create infinite loop)
            if indexing.status == IndexingStatus.FAILED and current_user.onboarding_completed and gmail_connected:
                try:
                    from app.tasks.indexing_tasks import index_user_emails
                    index_user_emails.delay(user_id=current_user.id, days_back=90)
                    logger.info(
                        "indexing_auto_retry_from_dashboard",
                        user_id=current_user.id,
                        reason="previous_indexing_failed",
                    )
                except Exception as trigger_error:
                    logger.warning(
                        "indexing_auto_trigger_failed",
                        user_id=current_user.id,
                        error=str(trigger_error),
                    )
        elif not indexing:
            # Auto-trigger indexing if user completed onboarding but indexing never started
            # This only runs ONCE - when no indexing record exists
            if current_user.onboarding_completed and gmail_connected:
                try:
                    from app.tasks.indexing_tasks import index_user_emails
                    index_user_emails.delay(user_id=current_user.id, days_back=90)
                    logger.info(
                        "indexing_auto_triggered_from_dashboard",
                        user_id=current_user.id,
                        reason="onboarding_complete_no_indexing_record",
                    )
                except Exception as trigger_error:
                    logger.warning(
                        "indexing_auto_trigger_failed",
                        user_id=current_user.id,
                        error=str(trigger_error),
                    )

        # Log dashboard stats retrieval
        logger.info(
            "dashboard_stats_retrieved",
            user_id=current_user.id,
            total_processed=total_processed,
            pending_approval=pending_approval,
            gmail_connected=gmail_connected,
            telegram_connected=telegram_connected,
        )

        # Return stats wrapped in 'data' field for frontend consistency
        stats_data = DashboardStatsResponse(
            total_processed=total_processed,
            pending_approval=pending_approval,
            auto_sorted=auto_sorted,
            responses_sent=responses_sent,
            gmail_connected=gmail_connected,
            telegram_connected=telegram_connected,
            vector_db_connected=vector_db_connected,
            indexing_in_progress=indexing_in_progress,
            indexing_total_emails=indexing_total_emails,
            indexing_processed_count=indexing_processed_count,
            indexing_progress_percent=indexing_progress_percent,
            indexing_status=indexing_status,
            indexing_error=indexing_error,
        )
        return {"data": stats_data}

    except Exception as e:
        logger.error(
            "error_retrieving_dashboard_stats",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Re-raise exception to let FastAPI handle it
        raise
