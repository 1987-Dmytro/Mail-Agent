"""Telegram account linking endpoints for Mail Agent bot integration."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from telegram import Update

from app.api.deps import get_db
from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.models.linking_codes import LinkingCode
from app.models.user import User
from app.services.telegram_linking import generate_linking_code

router = APIRouter()


# Pydantic schemas for request/response validation
class LinkingCodeData(BaseModel):
    """Data payload for linking code response."""

    code: str = Field(..., description="6-digit alphanumeric linking code")
    expires_at: str = Field(..., description="ISO timestamp when code expires")
    bot_username: str = Field(..., description="Telegram bot username (without @)")
    instructions: str = Field(..., description="User-friendly linking instructions")


class LinkingCodeResponse(BaseModel):
    """Response schema for linking code generation."""

    success: bool = Field(..., description="Whether code generation succeeded")
    data: LinkingCodeData


class TelegramStatusData(BaseModel):
    """Data payload for Telegram status response."""

    linked: bool = Field(..., description="Whether Telegram account is linked")
    telegram_id: str | None = Field(None, description="Telegram user ID if linked")
    telegram_username: str | None = Field(None, description="Telegram username if linked")
    linked_at: str | None = Field(None, description="ISO timestamp when account was linked")


class TelegramStatusResponse(BaseModel):
    """Response schema for Telegram linking status."""

    success: bool = Field(..., description="Whether status check succeeded")
    data: TelegramStatusData


@router.post("/link", response_model=LinkingCodeResponse, status_code=201)
@router.post("/generate-code", response_model=LinkingCodeResponse, status_code=201)
async def generate_telegram_linking_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate unique linking code for Telegram account connection.

    This endpoint:
    1. Validates user is not already linked to Telegram
    2. Generates cryptographically secure 6-digit code (A-Z, 0-9)
    3. Stores code in database with 15-minute expiration
    4. Returns code with bot username and linking instructions

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        LinkingCodeResponse: Code, expiration time, bot username, and instructions

    Raises:
        HTTPException 400: If Telegram account already linked
        HTTPException 500: If code generation fails

    Example:
        POST /api/v1/telegram/generate-code
        Authorization: Bearer <jwt_token>

        Response:
        {
            "success": true,
            "data": {
                "code": "A3B7X9",
                "expires_at": "2025-11-07T12:15:00Z",
                "bot_username": "MailAgentBot",
                "instructions": "Open Telegram, search for @MailAgentBot, and send: /start A3B7X9"
            }
        }
    """
    try:
        # Check if user already linked
        if current_user.telegram_id:
            logger.warning(
                "telegram_code_generation_rejected_already_linked",
                user_id=current_user.id,
                telegram_id=current_user.telegram_id
            )
            raise HTTPException(
                status_code=400,
                detail="Telegram account already linked. Unlink first if you want to reconnect."
            )

        # Generate code
        code = generate_linking_code(current_user.id, db)

        # Get code record for expires_at
        code_record = db.exec(
            select(LinkingCode).where(LinkingCode.code == code)
        ).first()

        if not code_record:
            logger.error(
                "linking_code_not_found_after_generation",
                user_id=current_user.id,
                code=code
            )
            raise HTTPException(
                status_code=500,
                detail="Code generation failed. Please try again."
            )

        logger.info(
            "telegram_code_generated_via_api",
            user_id=current_user.id,
            code=code,
            expires_at=code_record.expires_at.isoformat()
        )

        return LinkingCodeResponse(
            success=True,
            data=LinkingCodeData(
                code=code,
                expires_at=code_record.expires_at.isoformat(),
                bot_username=settings.TELEGRAM_BOT_USERNAME,
                instructions=f"Open Telegram, search for @{settings.TELEGRAM_BOT_USERNAME}, and send: /start {code}"
            )
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "telegram_code_generation_failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating linking code. Please try again."
        )


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    current_user: User = Depends(get_current_user),
):
    """Check if user's Telegram account is linked.

    This endpoint returns the current Telegram linking status for the authenticated user,
    including telegram_id, username, and linking timestamp if linked.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        TelegramStatusResponse: Linking status and Telegram account details

    Example:
        GET /api/v1/telegram/status
        Authorization: Bearer <jwt_token>

        Response (not linked):
        {
            "success": true,
            "data": {
                "linked": false,
                "telegram_id": null,
                "telegram_username": null,
                "linked_at": null
            }
        }

        Response (linked):
        {
            "success": true,
            "data": {
                "linked": true,
                "telegram_id": "123456789",
                "telegram_username": "john_doe",
                "linked_at": "2025-11-07T11:30:00Z"
            }
        }
    """
    logger.info(
        "telegram_status_checked",
        user_id=current_user.id,
        linked=bool(current_user.telegram_id)
    )

    return TelegramStatusResponse(
        success=True,
        data=TelegramStatusData(
            linked=bool(current_user.telegram_id),
            telegram_id=current_user.telegram_id,
            telegram_username=current_user.telegram_username,
            linked_at=current_user.telegram_linked_at.isoformat() if current_user.telegram_linked_at else None
        )
    )


class VerificationData(BaseModel):
    """Data payload for code verification response."""

    verified: bool = Field(..., description="Whether the linking code has been used")
    linked: bool = Field(..., description="Whether Telegram account is now linked")
    telegram_username: str | None = Field(None, description="Telegram username if linked")


class VerificationResponse(BaseModel):
    """Response schema for linking code verification."""

    success: bool = Field(..., description="Whether verification check succeeded")
    data: VerificationData


@router.get("/verify/{code}", response_model=VerificationResponse)
async def verify_linking_code(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify if a linking code has been used to complete Telegram account linking.

    This endpoint checks if the provided linking code has been successfully used
    by the Telegram bot to link the user's account. The frontend polls this endpoint
    to detect when the user has completed the Telegram linking process.

    Args:
        code: The 6-digit linking code to verify
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        VerificationResponse: Verification status and linking details

    Example:
        GET /api/v1/telegram/verify/A3B7X9
        Authorization: Bearer <jwt_token>

        Response (not yet verified):
        {
            "success": true,
            "data": {
                "verified": false,
                "linked": false,
                "telegram_username": null
            }
        }

        Response (verified and linked):
        {
            "success": true,
            "data": {
                "verified": true,
                "linked": true,
                "telegram_username": "john_doe"
            }
        }
    """
    try:
        # Find the linking code in database
        code_record = db.exec(
            select(LinkingCode).where(
                LinkingCode.code == code.upper(),
                LinkingCode.user_id == current_user.id
            )
        ).first()

        if not code_record:
            logger.warning(
                "verification_code_not_found",
                user_id=current_user.id,
                code=code
            )
            # Return not verified instead of error to avoid breaking polling
            return VerificationResponse(
                success=True,
                data=VerificationData(
                    verified=False,
                    linked=False,
                    telegram_username=None
                )
            )

        # Check if code has expired
        if code_record.expires_at < datetime.now(code_record.expires_at.tzinfo):
            logger.info(
                "verification_code_expired",
                user_id=current_user.id,
                code=code,
                expired_at=code_record.expires_at.isoformat()
            )
            return VerificationResponse(
                success=True,
                data=VerificationData(
                    verified=False,
                    linked=False,
                    telegram_username=None
                )
            )

        # Query user from database to get latest telegram_id
        # Note: current_user from auth dependency is not attached to this session,
        # so we need to query it fresh from the database
        user = db.exec(
            select(User).where(User.id == current_user.id)
        ).first()

        if not user:
            logger.error(
                "user_not_found_during_verification",
                user_id=current_user.id,
                code=code
            )
            raise HTTPException(
                status_code=500,
                detail="User not found. Please try again."
            )

        # Check if user now has telegram_id (meaning they completed linking)
        verified = bool(user.telegram_id)

        logger.info(
            "linking_code_verified",
            user_id=current_user.id,
            code=code,
            verified=verified,
            linked=verified
        )

        return VerificationResponse(
            success=True,
            data=VerificationData(
                verified=verified,
                linked=verified,
                telegram_username=user.telegram_username if verified else None
            )
        )

    except Exception as e:
        logger.error(
            "verification_check_failed",
            user_id=current_user.id,
            code=code,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while verifying linking code. Please try again."
        )


@router.post("/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    """Telegram webhook endpoint for receiving bot updates.

    This endpoint receives updates from Telegram servers when webhook mode is enabled.
    Only used in production deployments with multiple instances.

    Security:
    - Validates secret token from Telegram headers
    - Rejects requests without valid secret token

    Args:
        request: FastAPI request object with JSON body
        x_telegram_bot_api_secret_token: Secret token from Telegram

    Returns:
        Response with 200 OK if update processed successfully

    Raises:
        HTTPException 403: If secret token is invalid or missing
    """
    # Validate secret token (if configured)
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning(
                "telegram_webhook_invalid_secret",
                received_token=x_telegram_bot_api_secret_token[:10] if x_telegram_bot_api_secret_token else None,
            )
            raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        # Get telegram_bot instance from app state
        from app.main import telegram_bot

        if not telegram_bot or not telegram_bot.application:
            logger.error("telegram_webhook_bot_not_initialized")
            raise HTTPException(status_code=500, detail="Bot not initialized")

        # Parse update from request body
        body = await request.json()
        update = Update.de_json(body, telegram_bot.bot)

        # Process update through application handlers
        await telegram_bot.application.process_update(update)

        logger.info(
            "telegram_webhook_update_processed",
            update_id=update.update_id,
            has_message=bool(update.message),
            has_callback_query=bool(update.callback_query),
        )

        return Response(status_code=200)

    except Exception as e:
        logger.error(
            "telegram_webhook_processing_failed",
            error=str(e),
            exc_info=True,
        )
        # Return 200 to prevent Telegram from retrying
        # Log error for investigation
        return Response(status_code=200)
