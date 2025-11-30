"""Statistics endpoints for monitoring AI classification accuracy and error handling (Story 2.11)."""

from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.api.v1.auth import get_current_user
from app.api.deps import get_async_db
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.services.approval_history import ApprovalHistoryService
import structlog


router = APIRouter()
logger = structlog.get_logger(__name__)


# Pydantic schemas for response validation
class TopFolderItem(BaseModel):
    """Schema for top folder usage item."""

    name: str = Field(..., description="Folder name")
    count: int = Field(..., description="Number of times folder was selected")


class ApprovalStatisticsResponse(BaseModel):
    """Response schema for approval statistics."""

    success: bool = Field(True, description="Request success status")
    data: Dict[str, Any] = Field(..., description="Statistics data")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_decisions": 150,
                    "approved": 120,
                    "rejected": 20,
                    "folder_changed": 10,
                    "approval_rate": 0.867,
                    "top_folders": [
                        {"name": "Government", "count": 45},
                        {"name": "Clients", "count": 35}
                    ]
                }
            }
        }


@router.get("/approvals", response_model=ApprovalStatisticsResponse)
async def get_approval_statistics(
    from_date: Optional[datetime] = Query(
        None,
        alias="from",
        description="Start date for statistics (ISO 8601 format: 2025-11-01T00:00:00Z)",
        examples=["2025-11-01T00:00:00Z"]
    ),
    to_date: Optional[datetime] = Query(
        None,
        alias="to",
        description="End date for statistics (ISO 8601 format: 2025-11-30T23:59:59Z)",
        examples=["2025-11-30T23:59:59Z"]
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get approval decision statistics for the authenticated user.

    This endpoint provides aggregate statistics on user approval decisions:
    - total_decisions: Total number of approval/reject/change decisions
    - approved: Count of "approve" actions (user accepted AI suggestion)
    - rejected: Count of "reject" actions (user rejected email sorting)
    - folder_changed: Count of "change_folder" actions (user selected different folder)
    - approval_rate: AI acceptance rate = (approved + changed) / total (0.0-1.0)
    - top_folders: Top 5 most frequently selected folders with usage counts

    Args:
        from_date: Optional start date for statistics query (inclusive, timezone-aware UTC)
        to_date: Optional end date for statistics query (inclusive, timezone-aware UTC)
        current_user: Authenticated user from JWT token
        db: Async database session

    Returns:
        ApprovalStatisticsResponse: Statistics data with success=True

    Query Parameters:
        - from (datetime, optional): Start date (ISO 8601: 2025-11-01T00:00:00Z)
        - to (datetime, optional): End date (ISO 8601: 2025-11-30T23:59:59Z)

    Example Request:
        GET /api/v1/stats/approvals?from=2025-11-01T00:00:00Z&to=2025-11-30T23:59:59Z
        Headers:
            Authorization: Bearer {jwt_token}

    Example Response:
        {
            "success": true,
            "data": {
                "total_decisions": 150,
                "approved": 120,
                "rejected": 20,
                "folder_changed": 10,
                "approval_rate": 0.867,
                "top_folders": [
                    {"name": "Government", "count": 45},
                    {"name": "Clients", "count": 35},
                    {"name": "Personal", "count": 25},
                    {"name": "Marketing", "count": 20},
                    {"name": "Finance", "count": 15}
                ]
            }
        }
    """
    try:
        # Create approval history service
        approval_service = ApprovalHistoryService(db)

        # Get statistics from service (applies user_id filter automatically)
        statistics = await approval_service.get_approval_statistics(
            user_id=current_user.id,
            from_date=from_date,
            to_date=to_date,
        )

        # Log successful statistics retrieval
        logger.info(
            "approval_statistics_retrieved",
            user_id=current_user.id,
            from_date=from_date.isoformat() if from_date else None,
            to_date=to_date.isoformat() if to_date else None,
            total_decisions=statistics["total_decisions"],
        )

        # Return formatted response
        return ApprovalStatisticsResponse(
            success=True,
            data=statistics
        )

    except Exception as e:
        logger.error(
            "error_retrieving_approval_statistics",
            user_id=current_user.id,
            from_date=from_date.isoformat() if from_date else None,
            to_date=to_date.isoformat() if to_date else None,
            error=str(e),
            error_type=type(e).__name__,
        )
        # Re-raise exception to let FastAPI handle it
        raise


class ErrorStatisticsResponse(BaseModel):
    """Response schema for error statistics (Story 2.11 - AC #7)."""

    success: bool = Field(True, description="Request success status")
    data: Dict[str, Any] = Field(..., description="Error statistics data")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_errors": 15,
                    "errors_last_24h": 3,
                    "error_rate": 0.05,
                    "errors_by_type": {
                        "gmail_api_failure": 8,
                        "telegram_send_failure": 5,
                        "classification_failure": 2
                    },
                    "recent_errors": [
                        {
                            "email_id": 123,
                            "error_type": "gmail_api_failure",
                            "error_message": "503 Service Unavailable",
                            "timestamp": "2025-11-08T10:30:00Z",
                            "retry_count": 3
                        }
                    ],
                    "health_status": "healthy"
                }
            }
        }


@router.get("/errors", response_model=ErrorStatisticsResponse)
async def get_error_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get error statistics and health metrics for the authenticated user (Story 2.11 - AC #7).

    This endpoint provides comprehensive error tracking and system health metrics:
    - total_errors: Total count of emails in error status
    - errors_last_24h: Count of errors in last 24 hours
    - error_rate: Percentage of emails that failed (error / total processed)
    - errors_by_type: Breakdown of errors by type (gmail_api_failure, telegram_send_failure, etc.)
    - recent_errors: List of last 10 errors with details
    - health_status: Overall system health ("healthy", "degraded", "critical")

    Args:
        current_user: Authenticated user from JWT token
        db: Async database session

    Returns:
        ErrorStatisticsResponse: Error statistics and health metrics with success=True

    Example Request:
        GET /api/v1/stats/errors
        Headers:
            Authorization: Bearer {jwt_token}

    Example Response:
        {
            "success": true,
            "data": {
                "total_errors": 15,
                "errors_last_24h": 3,
                "error_rate": 0.05,
                "errors_by_type": {
                    "gmail_api_failure": 8,
                    "telegram_send_failure": 5,
                    "classification_failure": 2
                },
                "recent_errors": [
                    {
                        "email_id": 123,
                        "error_type": "gmail_api_failure",
                        "error_message": "503 Service Unavailable",
                        "timestamp": "2025-11-08T10:30:00Z",
                        "retry_count": 3,
                        "sender": "client@example.com",
                        "subject": "Important Project Update"
                    }
                ],
                "health_status": "healthy"
            }
        }
    """
    try:
        # Calculate 24h cutoff
        cutoff_24h = datetime.now(UTC) - timedelta(hours=24)

        # Query total errors
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "error"
            )
        )
        total_errors = result.scalar() or 0

        # Query errors in last 24h
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "error",
                EmailProcessingQueue.error_timestamp >= cutoff_24h
            )
        )
        errors_last_24h = result.scalar() or 0

        # Query total processed emails for error rate calculation
        result = await db.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(EmailProcessingQueue.user_id == current_user.id)
        )
        total_processed = result.scalar() or 0

        # Calculate error rate
        error_rate = (total_errors / total_processed) if total_processed > 0 else 0.0

        # Query errors by type
        result = await db.execute(
            select(
                EmailProcessingQueue.error_type,
                func.count(EmailProcessingQueue.id).label("count")
            )
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "error",
                EmailProcessingQueue.error_type.isnot(None)
            )
            .group_by(EmailProcessingQueue.error_type)
        )
        errors_by_type = {row.error_type: row.count for row in result}

        # Query recent errors (last 10)
        result = await db.execute(
            select(EmailProcessingQueue)
            .where(
                EmailProcessingQueue.user_id == current_user.id,
                EmailProcessingQueue.status == "error"
            )
            .order_by(EmailProcessingQueue.error_timestamp.desc())
            .limit(10)
        )
        recent_error_records = result.scalars().all()

        recent_errors = [
            {
                "email_id": email.id,
                "error_type": email.error_type,
                "error_message": email.error_message,
                "timestamp": email.error_timestamp.isoformat() if email.error_timestamp else None,
                "retry_count": email.retry_count,
                "sender": email.sender,
                "subject": email.subject or "(no subject)"
            }
            for email in recent_error_records
        ]

        # Determine health status based on error rate
        if error_rate < 0.05:  # < 5% error rate
            health_status = "healthy"
        elif error_rate < 0.15:  # 5-15% error rate
            health_status = "degraded"
        else:  # > 15% error rate
            health_status = "critical"

        # Log statistics retrieval
        logger.info(
            "error_statistics_retrieved",
            user_id=current_user.id,
            total_errors=total_errors,
            errors_last_24h=errors_last_24h,
            error_rate=error_rate,
            health_status=health_status,
        )

        # Return formatted response
        return ErrorStatisticsResponse(
            success=True,
            data={
                "total_errors": total_errors,
                "errors_last_24h": errors_last_24h,
                "error_rate": round(error_rate, 4),
                "errors_by_type": errors_by_type,
                "recent_errors": recent_errors,
                "health_status": health_status,
            }
        )

    except Exception as e:
        logger.error(
            "error_retrieving_error_statistics",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Re-raise exception to let FastAPI handle it
        raise
