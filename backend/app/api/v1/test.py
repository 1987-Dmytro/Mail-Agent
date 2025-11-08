"""Test endpoints for manual testing of Mail Agent features."""

import time
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.api.v1.auth import get_current_user
from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient
from app.core.logging import logger
from app.models.user import User
from app.services.database import DatabaseService, database_service
from app.utils.errors import (
    GeminiAPIError,
    GeminiInvalidRequestError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    InvalidRecipientError,
    MessageTooLargeError,
    QuotaExceededError,
    TelegramSendError,
    TelegramUserBlockedError,
)

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


class GeminiTestRequest(BaseModel):
    """Request model for Gemini API connectivity test.

    Attributes:
        prompt: The prompt text to send to Gemini
        response_format: Response format - "text" (default) or "json" for structured output
    """

    prompt: str = Field(
        ...,
        example="Classify this email: From finanzamt@berlin.de Subject: Tax deadline. Body: Your tax documents are due next week.",
    )
    response_format: str = Field("text", example="json")


class GeminiTestResponse(BaseModel):
    """Response model for Gemini API connectivity test.

    Attributes:
        success: Whether the API call was successful
        data: Response data containing AI output, tokens used, and latency
    """

    success: bool
    data: dict = Field(
        ...,
        example={
            "response": {"suggested_folder": "Government", "reasoning": "Email from tax office", "priority_score": 85},
            "tokens_used": 42,
            "latency_ms": 1850,
        },
    )


@router.post("/gemini", status_code=status.HTTP_200_OK, response_model=GeminiTestResponse)
def test_gemini_connectivity(
    request: GeminiTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Test Gemini API connectivity and response generation.

    This endpoint allows authenticated users to test the Gemini LLM integration.
    Supports both text and JSON response formats for various use cases.

    Requires:
        - Valid JWT authentication token
        - GEMINI_API_KEY environment variable configured

    Args:
        request: Gemini test request with prompt and response format
        current_user: Authenticated user from JWT token

    Returns:
        JSON response with success status and AI response:
        {
            "success": true,
            "data": {
                "response": "AI-generated response text or JSON object",
                "tokens_used": 42,
                "latency_ms": 1850
            }
        }

    Raises:
        HTTPException 400: Invalid request (blocked prompt, malformed parameters)
        HTTPException 429: Rate limit exceeded (1M tokens/minute)
        HTTPException 408: Request timeout (> 30 seconds)
        HTTPException 500: Internal server error (Gemini API failure)

    Example (text mode):
        POST /api/v1/test/gemini
        Headers: Authorization: Bearer <jwt_token>
        Body:
        {
            "prompt": "Explain quantum computing in 2 sentences",
            "response_format": "text"
        }

    Example (JSON mode):
        POST /api/v1/test/gemini
        Body:
        {
            "prompt": "Classify this email: From tax@gov.de Subject: Tax deadline",
            "response_format": "json"
        }
    """
    logger.info(
        "gemini_test_requested",
        user_id=current_user.id,
        prompt_length=len(request.prompt),
        response_format=request.response_format,
    )

    # Validate response_format
    if request.response_format not in ["text", "json"]:
        logger.error(
            "gemini_test_invalid_format",
            user_id=current_user.id,
            response_format=request.response_format,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"response_format must be 'text' or 'json', got: {request.response_format}",
        )

    try:
        # Initialize LLM client
        llm_client = LLMClient()

        # Get prompt version for classification prompts
        from app.prompts import CLASSIFICATION_PROMPT_VERSION

        # Track latency
        start_time = time.time()

        # Call Gemini API
        if request.response_format == "json":
            response_data = llm_client.receive_completion(request.prompt, operation="test")
        else:
            response_text = llm_client.send_prompt(request.prompt, response_format="text", operation="test")
            response_data = {"response": response_text}

        latency_ms = int((time.time() - start_time) * 1000)

        # Get token usage
        token_stats = llm_client.get_token_usage_stats()
        tokens_used = token_stats["total_tokens"]

        logger.info(
            "gemini_test_completed",
            user_id=current_user.id,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            response_format=request.response_format,
            prompt_version=CLASSIFICATION_PROMPT_VERSION,
        )

        return GeminiTestResponse(
            success=True,
            data={
                "response": response_data,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "prompt_version": CLASSIFICATION_PROMPT_VERSION,
            },
        )

    except GeminiInvalidRequestError as e:
        logger.error(
            "gemini_test_invalid_request",
            user_id=current_user.id,
            error=str(e),
            prompt_preview=e.prompt_preview,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        )

    except GeminiRateLimitError as e:
        logger.error(
            "gemini_test_rate_limit",
            user_id=current_user.id,
            error=str(e),
            retry_after=e.retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini API rate limit exceeded (1M tokens/minute). Please try again in a moment.",
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else {},
        )

    except GeminiTimeoutError as e:
        logger.error(
            "gemini_test_timeout",
            user_id=current_user.id,
            error=str(e),
            timeout_seconds=e.timeout_seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Gemini request timed out after {e.timeout_seconds} seconds. Please try again.",
        )

    except GeminiAPIError as e:
        logger.error(
            "gemini_test_api_error",
            user_id=current_user.id,
            error=str(e),
            status_code=e.status_code,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API error. Please check your API key configuration and try again.",
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "gemini_test_unexpected_error",
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during Gemini API test. Please try again.",
        )


class TelegramTestRequest(BaseModel):
    """Request model for Telegram bot connectivity test.

    Attributes:
        message: The test message to send (default provided)
    """

    message: str = Field("Test notification from Mail Agent", example="Hello from Mail Agent Bot!")


class TelegramTestResponse(BaseModel):
    """Response model for Telegram bot connectivity test.

    Attributes:
        success: Whether the message was sent successfully
        data: Response data containing message_id, telegram_id, and timestamp
    """

    success: bool
    data: dict = Field(
        ...,
        example={
            "message_id": "12345",
            "sent_to": "123456789",
            "sent_at": "2024-01-15T10:30:00.000Z",
        },
    )


@router.post("/telegram", status_code=status.HTTP_200_OK, response_model=TelegramTestResponse)
async def test_telegram_connectivity(
    request: TelegramTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Test Telegram bot connectivity by sending a test message.

    This endpoint allows authenticated users to verify their Telegram bot connection
    by sending a test message to their linked Telegram account.

    Requires:
        - Valid JWT authentication token
        - User must have linked Telegram account (telegram_id field populated)
        - TELEGRAM_BOT_TOKEN environment variable configured

    Args:
        request: Test request with optional custom message
        current_user: Authenticated user from JWT token

    Returns:
        JSON response with success status and message details:
        {
            "success": true,
            "data": {
                "message_id": "12345",
                "sent_to": "123456789",
                "sent_at": "2024-01-15T10:30:00.000Z"
            }
        }

    Raises:
        HTTPException 400: Telegram account not linked
        HTTPException 403: User has blocked the bot
        HTTPException 500: Failed to send message (network error, bot not configured)

    Example:
        POST /api/v1/test/telegram
        Headers: Authorization: Bearer <jwt_token>
        Body:
        {
            "message": "Testing Telegram notifications"
        }
    """
    logger.info(
        "telegram_test_requested",
        user_id=current_user.id,
        telegram_id=current_user.telegram_id,
    )

    # Check if user has linked Telegram account
    if not current_user.telegram_id:
        logger.error(
            "telegram_test_no_account_linked",
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account not linked. Please link your Telegram account first using /start command in the bot.",
        )

    try:
        # Import telegram_bot from main.py (global instance)
        from app.main import telegram_bot

        # Send test message
        message_id = await telegram_bot.send_message(
            telegram_id=str(current_user.telegram_id),
            text=f"*Test Message* ✅\n\n{request.message}\n\n_Sent at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC_",
        )

        logger.info(
            "telegram_test_sent_successfully",
            user_id=current_user.id,
            telegram_id=current_user.telegram_id,
            message_id=message_id,
        )

        return TelegramTestResponse(
            success=True,
            data={
                "message_id": message_id,
                "sent_to": str(current_user.telegram_id),
                "sent_at": datetime.now(UTC).isoformat(),
            },
        )

    except TelegramUserBlockedError as e:
        logger.error(
            "telegram_test_user_blocked",
            user_id=current_user.id,
            telegram_id=current_user.telegram_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have blocked the bot. Please unblock it in Telegram and try again.",
        )

    except TelegramSendError as e:
        logger.error(
            "telegram_test_send_error",
            user_id=current_user.id,
            telegram_id=current_user.telegram_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test message: {str(e)}",
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "telegram_test_unexpected_error",
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test message. Please check your Telegram bot configuration.",
        )
