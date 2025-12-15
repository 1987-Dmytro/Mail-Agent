"""Folder management endpoints for organizing emails into user-defined categories."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.services.folder_service import FolderService

router = APIRouter()


# Pydantic schemas for request/response validation
class FolderCreateRequest(BaseModel):
    """Request schema for creating a new folder."""

    name: str = Field(..., min_length=1, max_length=100, description="Folder display name")
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords for AI classification hints (Epic 2)",
    )
    color: str | None = Field(
        None,
        min_length=7,
        max_length=7,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code (e.g., #FF5733)",
    )


class FolderResponse(BaseModel):
    """Response schema for folder data."""

    id: int
    user_id: int
    name: str
    gmail_label_id: str | None
    keywords: List[str]
    color: str | None
    is_default: bool
    created_at: str  # ISO datetime string
    updated_at: str  # ISO datetime string

    class Config:
        """Pydantic config for ORM compatibility."""

        from_attributes = True


@router.post("", status_code=201)
async def create_folder(
    folder_data: FolderCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new folder category for the authenticated user.

    This endpoint:
    1. Validates folder name and color format
    2. Creates a Gmail label via Gmail API
    3. Stores folder record in database with gmail_label_id

    Args:
        folder_data: Folder creation request with name, keywords, and color
        current_user: Authenticated user from JWT token

    Returns:
        dict: Response with 'data' key containing created folder

    Raises:
        HTTPException 400: If folder name is invalid or duplicate exists
        HTTPException 500: If Gmail API call fails

    Example:
        POST /api/v1/folders/
        {
            "name": "Government",
            "keywords": ["finanzamt", "tax", "ausländerbehörde"],
            "color": "#FF5733"
        }

        Response:
        {
            "data": {
                "id": 5,
                "user_id": 1,
                "name": "Government",
                "gmail_label_id": "Label_123",
                "keywords": ["finanzamt", "tax", "ausländerbehörde"],
                "color": "#FF5733",
                "is_default": false,
                "created_at": "2025-11-05T12:00:00Z",
                "updated_at": "2025-11-05T12:00:00Z"
            }
        }
    """
    try:
        folder_service = FolderService()
        folder = await folder_service.create_folder(
            user_id=current_user.id,
            name=folder_data.name,
            keywords=folder_data.keywords,
            color=folder_data.color,
        )

        logger.info(
            "folder_created_via_api",
            user_id=current_user.id,
            folder_id=folder.id,
            folder_name=folder.name,
        )

        # Convert datetime to ISO string and wrap in 'data' field
        folder_response = FolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            name=folder.name,
            gmail_label_id=folder.gmail_label_id,
            keywords=folder.keywords,
            color=folder.color,
            is_default=folder.is_default,
            created_at=folder.created_at.isoformat(),
            updated_at=folder.updated_at.isoformat(),
        )

        return {"data": folder_response}

    except ValueError as e:
        # Validation error (invalid name or duplicate)
        logger.warning(
            "folder_creation_validation_error",
            user_id=current_user.id,
            folder_name=folder_data.name,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Gmail API or database error
        logger.error(
            "folder_creation_error",
            user_id=current_user.id,
            folder_name=folder_data.name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create folder. Please try again later.",
        )


@router.get("")
async def list_folders(
    current_user: User = Depends(get_current_user),
):
    """List all folders for the authenticated user.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        dict: Response with 'data' key containing list of folders

    Example:
        GET /api/v1/folders/

        Response:
        {
            "data": [
                {
                    "id": 5,
                    "user_id": 1,
                    "name": "Government",
                    "gmail_label_id": "Label_123",
                    "keywords": ["finanzamt", "tax"],
                    "color": "#FF5733",
                    "is_default": false,
                    "created_at": "2025-11-05T12:00:00Z",
                    "updated_at": "2025-11-05T12:00:00Z"
                },
                ...
            ]
        }
    """
    try:
        folder_service = FolderService()
        folders = await folder_service.list_folders(user_id=current_user.id)

        logger.info(
            "folders_listed_via_api",
            user_id=current_user.id,
            folder_count=len(folders),
        )

        # Convert to response schema and wrap in 'data' field
        folders_list = [
            FolderResponse(
                id=folder.id,
                user_id=folder.user_id,
                name=folder.name,
                gmail_label_id=folder.gmail_label_id,
                keywords=folder.keywords,
                color=folder.color,
                is_default=folder.is_default,
                created_at=folder.created_at.isoformat(),
                updated_at=folder.updated_at.isoformat(),
            )
            for folder in folders
        ]

        return {"data": folders_list}

    except Exception as e:
        logger.error(
            "folders_list_error",
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to list folders. Please try again later.",
        )


@router.get("/{folder_id}")
async def get_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get a single folder by ID.

    Args:
        folder_id: The folder ID to retrieve
        current_user: Authenticated user from JWT token

    Returns:
        dict: Response with 'data' key containing folder

    Raises:
        HTTPException 404: If folder not found or not owned by user

    Example:
        GET /api/v1/folders/5

        Response:
        {
            "data": {
                "id": 5,
                "user_id": 1,
                "name": "Government",
                "gmail_label_id": "Label_123",
                ...
            }
        }
    """
    try:
        folder_service = FolderService()
        folder = await folder_service.get_folder_by_id(
            folder_id=folder_id,
            user_id=current_user.id,
        )

        if not folder:
            logger.warning(
                "folder_not_found_via_api",
                user_id=current_user.id,
                folder_id=folder_id,
            )
            raise HTTPException(status_code=404, detail="Folder not found")

        logger.info(
            "folder_fetched_via_api",
            user_id=current_user.id,
            folder_id=folder_id,
            folder_name=folder.name,
        )

        folder_response = FolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            name=folder.name,
            gmail_label_id=folder.gmail_label_id,
            keywords=folder.keywords,
            color=folder.color,
            is_default=folder.is_default,
            created_at=folder.created_at.isoformat(),
            updated_at=folder.updated_at.isoformat(),
        )

        return {"data": folder_response}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "folder_fetch_error",
            user_id=current_user.id,
            folder_id=folder_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch folder. Please try again later.",
        )


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a folder category.

    This endpoint:
    1. Verifies folder ownership
    2. Deletes folder from database (Gmail label remains in Gmail)

    Note: Gmail label is NOT deleted from Gmail. User can manually delete it in Gmail UI.

    Args:
        folder_id: The folder ID to delete
        current_user: Authenticated user from JWT token

    Raises:
        HTTPException 404: If folder not found or not owned by user

    Example:
        DELETE /api/v1/folders/5

        Response: 204 No Content
    """
    try:
        folder_service = FolderService()
        success = await folder_service.delete_folder(
            folder_id=folder_id,
            user_id=current_user.id,
        )

        if not success:
            logger.warning(
                "folder_not_found_for_deletion_via_api",
                user_id=current_user.id,
                folder_id=folder_id,
            )
            raise HTTPException(status_code=404, detail="Folder not found")

        logger.info(
            "folder_deleted_via_api",
            user_id=current_user.id,
            folder_id=folder_id,
        )

        return None  # 204 No Content

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "folder_deletion_error",
            user_id=current_user.id,
            folder_id=folder_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete folder. Please try again later.",
        )
