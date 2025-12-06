"""Admin dashboard endpoints for monitoring system errors (Story 2.11 - AC #7)."""

from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.api.deps import get_async_db
from app.core.config import settings
from app.models.email import EmailProcessingQueue
import structlog


router = APIRouter()
logger = structlog.get_logger(__name__)


class ErrorItem(BaseModel):
    """Schema for individual error item in admin dashboard."""

    email_id: int = Field(..., description="Email processing queue ID")
    user_id: int = Field(..., description="User ID who owns the email")
    sender: str = Field(..., description="Email sender address")
    subject: str = Field(..., description="Email subject")
    error_type: Optional[str] = Field(None, description="Error type (e.g., gmail_api_failure)")
    error_message: Optional[str] = Field(None, description="Detailed error message")
    error_timestamp: Optional[str] = Field(None, description="ISO timestamp when error occurred")
    retry_count: int = Field(..., description="Number of retry attempts made")
    status: str = Field(..., description="Current status (error or dead_letter)")
    dlq_reason: Optional[str] = Field(None, description="Dead letter queue reason if applicable")


class AdminErrorsResponse(BaseModel):
    """Response schema for admin errors endpoint (AC #7)."""

    success: bool = Field(True, description="Request success status")
    data: Dict[str, Any] = Field(..., description="Admin error dashboard data")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_errors": 12,
                    "errors": [
                        {
                            "email_id": 123,
                            "user_id": 45,
                            "sender": "finanzamt@berlin.de",
                            "subject": "Tax Deadline",
                            "error_type": "gmail_api_failure",
                            "error_message": "HttpError 503: Service Unavailable",
                            "error_timestamp": "2025-11-08T14:30:00Z",
                            "retry_count": 3,
                            "status": "error",
                            "dlq_reason": None
                        }
                    ]
                }
            }
        }


def verify_admin_key(x_admin_api_key: str = Header(..., alias="X-Admin-Api-Key")) -> None:
    """Verify admin API key from request header.

    Args:
        x_admin_api_key: Admin API key from X-Admin-Api-Key header

    Raises:
        HTTPException: 401 Unauthorized if API key is invalid or missing

    Example:
        Headers:
            X-Admin-Api-Key: your-secret-admin-key
    """
    if not hasattr(settings, 'ADMIN_API_KEY') or not settings.ADMIN_API_KEY:
        logger.error(
            "admin_api_key_not_configured",
            message="ADMIN_API_KEY not set in environment variables"
        )
        raise HTTPException(
            status_code=500,
            detail="Admin API key not configured on server"
        )

    if x_admin_api_key != settings.ADMIN_API_KEY:
        logger.warning(
            "admin_api_key_invalid",
            message="Invalid admin API key provided"
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid admin API key"
        )


@router.get("/errors", response_model=AdminErrorsResponse)
async def get_admin_errors(
    user_id: Optional[int] = Query(None, description="Filter errors for specific user"),
    error_type: Optional[str] = Query(None, description="Filter by error type (gmail_api_failure, telegram_send_failure, etc.)"),
    from_date: Optional[datetime] = Query(None, description="Errors after this timestamp (ISO format)"),
    to_date: Optional[datetime] = Query(None, description="Errors before this timestamp (ISO format)"),
    status: Optional[str] = Query("error", description="Filter by status (error, dead_letter, or null for all)"),
    limit: int = Query(50, description="Maximum number of results to return", ge=1, le=500),
    db: AsyncSession = Depends(get_async_db),
    _admin: None = Depends(verify_admin_key),
):
    """Get emails in error state for admin dashboard (Story 2.11 - AC #7).

    This admin-only endpoint shows ALL users' emails in error status, with filtering capabilities.
    Requires admin authentication via X-Admin-Api-Key header.

    Args:
        user_id: Optional filter for specific user's errors
        error_type: Optional filter by error type
        from_date: Optional filter for errors after this timestamp
        to_date: Optional filter for errors before this timestamp
        status: Filter by status (default: "error", options: "error", "dead_letter", null for all)
        limit: Maximum results (default: 50, max: 500)
        db: Async database session
        _admin: Admin authentication dependency (auto-verified)

    Returns:
        AdminErrorsResponse: List of emails in error state with total count

    Security:
        Requires X-Admin-Api-Key header matching ADMIN_API_KEY environment variable

    Example Request:
        GET /api/v1/admin/errors?error_type=gmail_api_failure&limit=10
        Headers:
            X-Admin-Api-Key: {admin_api_key}

    Example Response:
        {
            "success": true,
            "data": {
                "total_errors": 12,
                "errors": [
                    {
                        "email_id": 123,
                        "user_id": 45,
                        "sender": "client@example.com",
                        "subject": "Important Update",
                        "error_type": "gmail_api_failure",
                        "error_message": "503 Service Unavailable",
                        "error_timestamp": "2025-11-08T14:30:00Z",
                        "retry_count": 3,
                        "status": "error",
                        "dlq_reason": null
                    }
                ]
            }
        }
    """
    try:
        # Build base query with filters
        conditions = []

        # Status filter
        if status:
            conditions.append(EmailProcessingQueue.status == status)
        else:
            # If no status specified, show both error and dead_letter
            conditions.append(EmailProcessingQueue.status.in_(["error", "dead_letter"]))

        # User filter
        if user_id is not None:
            conditions.append(EmailProcessingQueue.user_id == user_id)

        # Error type filter
        if error_type:
            conditions.append(EmailProcessingQueue.error_type == error_type)

        # Date range filters
        if from_date:
            conditions.append(EmailProcessingQueue.error_timestamp >= from_date)
        if to_date:
            conditions.append(EmailProcessingQueue.error_timestamp <= to_date)

        # Query total count
        count_query = select(func.count(EmailProcessingQueue.id)).where(*conditions)
        result = await db.execute(count_query)
        total_errors = result.scalar() or 0

        # Query error records with limit
        errors_query = (
            select(EmailProcessingQueue)
            .where(*conditions)
            .order_by(EmailProcessingQueue.error_timestamp.desc())
            .limit(limit)
        )
        result = await db.execute(errors_query)
        error_records = result.scalars().all()

        # Format error list
        errors = [
            {
                "email_id": email.id,
                "user_id": email.user_id,
                "sender": email.sender,
                "subject": email.subject or "(no subject)",
                "error_type": email.error_type,
                "error_message": email.error_message,
                "error_timestamp": email.error_timestamp.isoformat() if email.error_timestamp else None,
                "retry_count": email.retry_count or 0,
                "status": email.status,
                "dlq_reason": email.dlq_reason,
            }
            for email in error_records
        ]

        # Log admin access
        logger.info(
            "admin_errors_retrieved",
            total_errors=total_errors,
            returned_count=len(errors),
            filters={
                "user_id": user_id,
                "error_type": error_type,
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
                "status": status,
                "limit": limit,
            }
        )

        return AdminErrorsResponse(
            success=True,
            data={
                "total_errors": total_errors,
                "errors": errors,
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions (auth failures)
        raise
    except Exception as e:
        logger.error(
            "error_retrieving_admin_errors",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve admin errors"
        )


@router.post("/reindex-emails")
async def reindex_emails(
    user_id: int = Query(..., description="User ID"),
    start_id: int = Query(..., description="Start email ID"),
    end_id: int = Query(..., description="End email ID"),
    _: None = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Trigger reindexing of existing emails for ChromaDB.

    This endpoint queues a batch reindexing task for emails that were received
    before incremental indexing was enabled.

    Args:
        user_id: User ID
        start_id: Start of email ID range (inclusive)
        end_id: End of email ID range (inclusive)

    Returns:
        dict with task_id and queued count

    Example:
        POST /api/v1/admin/reindex-emails?user_id=3&start_id=252&end_id=261
        Headers:
            X-Admin-Api-Key: your-secret-admin-key
    """
    from app.tasks.indexing_tasks import reindex_email_batch

    logger.info(
        "reindex_emails_requested",
        user_id=user_id,
        start_id=start_id,
        end_id=end_id,
    )

    try:
        # Queue reindexing task
        task = reindex_email_batch.delay(
            user_id=user_id,
            start_id=start_id,
            end_id=end_id
        )

        logger.info(
            "reindex_emails_task_queued",
            task_id=task.id,
            user_id=user_id,
            start_id=start_id,
            end_id=end_id,
        )

        return {
            "success": True,
            "task_id": task.id,
            "message": f"Reindexing task queued for emails {start_id}-{end_id}",
            "user_id": user_id,
        }

    except Exception as e:
        logger.error(
            "reindex_emails_failed",
            user_id=user_id,
            start_id=start_id,
            end_id=end_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue reindexing task: {str(e)}"
        )
