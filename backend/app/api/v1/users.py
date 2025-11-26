"""User management endpoints.

This module provides endpoints for user profile management and updates.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.user import User
from app.services.database import database_service

router = APIRouter()


class UpdateUserRequest(BaseModel):
    """Request model for updating user data.

    Attributes:
        onboarding_completed: Whether user completed onboarding wizard
    """
    onboarding_completed: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for user data.

    Attributes:
        id: User ID
        email: User email
        gmail_connected: Whether Gmail is connected
        telegram_connected: Whether Telegram is connected
        onboarding_completed: Whether user completed onboarding
        created_at: When user was created
        updated_at: When user was last updated
    """
    id: int
    email: str
    gmail_connected: bool
    telegram_connected: bool
    onboarding_completed: bool
    created_at: str
    updated_at: str


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Update current user's profile data.

    This endpoint allows updating user profile fields like onboarding completion status.
    Only the authenticated user can update their own profile.

    Args:
        update_data: The fields to update
        current_user: The authenticated user (from JWT token)

    Returns:
        UserResponse: The updated user data

    Raises:
        HTTPException: If user not found or update fails
    """
    try:
        # Update only provided fields
        if update_data.onboarding_completed is not None:
            current_user.onboarding_completed = update_data.onboarding_completed
            logger.info(
                "user_onboarding_status_updated",
                user_id=current_user.id,
                onboarding_completed=update_data.onboarding_completed,
            )

        # Save to database
        updated_user = await database_service.update_user(current_user)

        # Build response
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            gmail_connected=bool(updated_user.gmail_oauth_token),
            telegram_connected=bool(updated_user.telegram_id),
            onboarding_completed=updated_user.onboarding_completed,
            created_at=updated_user.created_at.isoformat(),
            updated_at=updated_user.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(
            "user_update_failed",
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile",
        ) from e


@router.post("/complete-onboarding")
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
):
    """Mark user's onboarding as completed.

    Sets the onboarding_completed flag to True for the authenticated user.
    This endpoint is called by the frontend when the user finishes the
    onboarding wizard (Epic 4).

    Args:
        current_user: The authenticated user from JWT token

    Returns:
        dict: Success status and confirmation message

    Raises:
        HTTPException: If database update fails

    Example:
        POST /api/v1/users/complete-onboarding
        Authorization: Bearer <jwt_token>

        Response:
        {
            "success": true,
            "message": "Onboarding completed successfully"
        }
    """
    try:
        # Set onboarding_completed flag
        current_user.onboarding_completed = True

        # Persist to database
        await database_service.update_user(current_user)

        logger.info(
            "onboarding_completed",
            user_id=current_user.id,
            email=current_user.email,
        )

        return {
            "success": True,
            "message": "Onboarding completed successfully",
        }

    except Exception as e:
        logger.error(
            "onboarding_completion_failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete onboarding: {str(e)}",
        )
