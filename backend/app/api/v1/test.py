"""Test endpoints for manual testing of Mail Agent features."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.v1.auth import get_current_user
from app.core.gmail_client import GmailClient
from app.core.logging import logger
from app.models.user import User
from app.services.database import DatabaseService, database_service
from app.utils.errors import InvalidRecipientError, MessageTooLargeError, QuotaExceededError

router = APIRouter()


class SendEmailTestRequest(BaseModel):
    """Request model for test email sending endpoint.

    Attributes:
        to: Recipient email address
        subject: Email subject line
        body: Email body content (plain text or HTML)
        body_type: Body content type - "plain" or "html" (default: "plain")
        thread_id: Optional Gmail thread ID for threading (reply-to functionality)
    """

    to: EmailStr
    subject: str
    body: str
    body_type: str = "plain"
    thread_id: Optional[str] = None


class SendEmailTestResponse(BaseModel):
    """Response model for test email sending endpoint.

    Attributes:
        success: Whether email was sent successfully
        data: Response data containing message_id, recipient, and subject
    """

    success: bool
    data: dict


@router.post("/send-email", status_code=status.HTTP_200_OK, response_model=SendEmailTestResponse)
async def send_test_email(
    request: SendEmailTestRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(lambda: database_service),
):
    """Send a test email via Gmail API.

    This endpoint allows authenticated users to test email sending functionality.
    Supports plain text and HTML bodies, as well as reply-to-thread functionality.

    Requires:
        - Valid JWT authentication token
        - User must have connected Gmail account (OAuth tokens configured)

    Args:
        request: Email sending request with recipient, subject, body, etc.
        current_user: Authenticated user from JWT token

    Returns:
        JSON response with success status and message details:
        {
            "success": true,
            "data": {
                "message_id": "18abc123def456",
                "recipient": "recipient@example.com",
                "subject": "Test Email"
            }
        }

    Raises:
        HTTPException 400: Invalid recipient or malformed email
        HTTPException 413: Email exceeds 25MB size limit
        HTTPException 429: Gmail API quota exceeded (100 sends/day)
        HTTPException 500: Internal server error (Gmail API failure)

    Example:
        POST /api/v1/test/send-email
        Headers: Authorization: Bearer <jwt_token>
        Body:
        {
            "to": "recipient@example.com",
            "subject": "Test Email",
            "body": "This is a test message",
            "body_type": "plain"
        }

    Example with HTML:
        POST /api/v1/test/send-email
        Body:
        {
            "to": "recipient@example.com",
            "subject": "HTML Test",
            "body": "<h1>Hello</h1><p>This is HTML</p>",
            "body_type": "html"
        }

    Example with thread reply:
        POST /api/v1/test/send-email
        Body:
        {
            "to": "recipient@example.com",
            "subject": "Re: Original Subject",
            "body": "This is a reply",
            "thread_id": "thread_abc123"
        }
    """
    logger.info(
        "test_email_send_requested",
        user_id=current_user.id,
        recipient=request.to,
        subject=request.subject,
        body_type=request.body_type,
        has_thread=bool(request.thread_id),
    )

    # Validate body_type
    if request.body_type not in ["plain", "html"]:
        logger.error(
            "test_email_invalid_body_type",
            user_id=current_user.id,
            body_type=request.body_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"body_type must be 'plain' or 'html', got: {request.body_type}",
        )

    # Initialize Gmail client
    gmail_client = GmailClient(user_id=current_user.id, db_service=db_service)

    try:
        # Send email
        message_id = await gmail_client.send_email(
            to=request.to,
            subject=request.subject,
            body=request.body,
            body_type=request.body_type,
            thread_id=request.thread_id,
        )

        logger.info(
            "test_email_sent_successfully",
            user_id=current_user.id,
            recipient=request.to,
            message_id=message_id,
        )

        return SendEmailTestResponse(
            success=True,
            data={
                "message_id": message_id,
                "recipient": request.to,
                "subject": request.subject,
            },
        )

    except InvalidRecipientError as e:
        logger.error(
            "test_email_invalid_recipient",
            user_id=current_user.id,
            recipient=e.recipient,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recipient email address: {e.recipient}",
        )

    except QuotaExceededError as e:
        logger.error(
            "test_email_quota_exceeded",
            user_id=current_user.id,
            error=str(e),
            retry_after=e.retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gmail API quota exceeded (100 sends/day). Please try again tomorrow.",
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else {},
        )

    except MessageTooLargeError as e:
        logger.error(
            "test_email_message_too_large",
            user_id=current_user.id,
            error=str(e),
            size_bytes=e.size_bytes,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Email exceeds Gmail 25MB size limit (including attachments).",
        )

    except ValueError as e:
        # Invalid parameters (e.g., user has no email configured)
        logger.error(
            "test_email_invalid_params",
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "test_email_send_failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please check your Gmail connection and try again.",
        )
