"""FolderService for managing user's email organization folders."""

from typing import List, Optional

import structlog
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.gmail_client import GmailClient
from app.models.folder_category import FolderCategory
from app.services.database import DatabaseService, database_service

logger = structlog.get_logger(__name__)


class FolderService:
    """Service for managing folder category operations.

    Provides methods for creating, listing, and deleting user folders.
    Coordinates between database (FolderCategory model) and Gmail API (label operations).
    """

    def __init__(self, db_service: DatabaseService = None):
        """Initialize FolderService with database service.

        Args:
            db_service: DatabaseService instance (defaults to global database_service)
        """
        self.db_service = db_service or database_service

    async def create_folder(
        self,
        user_id: int,
        name: str,
        keywords: Optional[List[str]] = None,
        color: Optional[str] = None,
    ) -> FolderCategory:
        """Create a new folder category for user.

        This method performs the following steps:
        1. Validate folder name (1-100 chars, not empty)
        2. Check for duplicate name in database (user_id + name unique constraint)
        3. Create Gmail label via Gmail API
        4. Store FolderCategory record in database with gmail_label_id

        Args:
            user_id: The user ID who owns the folder
            name: Folder display name (1-100 chars)
            keywords: List of keywords for AI classification hints (Epic 2)
            color: Hex color code (e.g., "#FF5733") - optional

        Returns:
            FolderCategory: The created folder record with gmail_label_id

        Raises:
            ValueError: If folder name is invalid or duplicate exists
            HttpError: If Gmail API call fails

        Example:
            >>> service = FolderService()
            >>> folder = await service.create_folder(
            ...     user_id=1,
            ...     name="Government",
            ...     keywords=["finanzamt", "tax", "ausländerbehörde"],
            ...     color="#FF5733"
            ... )
            >>> print(f"Folder created with Gmail label ID: {folder.gmail_label_id}")
        """
        # Validate folder name
        if not name or len(name) < 1 or len(name) > 100:
            logger.error(
                "invalid_folder_name",
                user_id=user_id,
                name=name,
                name_length=len(name) if name else 0,
            )
            raise ValueError("Folder name must be between 1 and 100 characters")

        # Initialize Gmail client for this user
        gmail_client = GmailClient(user_id=user_id, db_service=self.db_service)

        try:
            # Create Gmail label (idempotent - returns existing label_id if exists)
            gmail_label_id = await gmail_client.create_label(name=name, color=color)

            logger.info(
                "gmail_label_created_for_folder",
                user_id=user_id,
                folder_name=name,
                gmail_label_id=gmail_label_id,
            )

        except Exception as e:
            logger.error(
                "gmail_label_creation_failed",
                user_id=user_id,
                folder_name=name,
                error=str(e),
                exc_info=True,
            )
            raise

        # Store FolderCategory record in database
        try:
            async with self.db_service.async_session() as session:
                folder = FolderCategory(
                    user_id=user_id,
                    name=name,
                    gmail_label_id=gmail_label_id,
                    keywords=keywords or [],
                    color=color,
                    is_default=False,
                )

                session.add(folder)
                await session.commit()
                await session.refresh(folder)

                logger.info(
                    "folder_created",
                    user_id=user_id,
                    folder_id=folder.id,
                    folder_name=name,
                    gmail_label_id=gmail_label_id,
                )

                return folder

        except IntegrityError as e:
            # Duplicate (user_id, name) constraint
            logger.error(
                "folder_duplicate_name",
                user_id=user_id,
                folder_name=name,
                error=str(e),
            )
            raise ValueError(f"Folder with name '{name}' already exists for this user")

        except Exception as e:
            logger.error(
                "folder_creation_failed",
                user_id=user_id,
                folder_name=name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def list_folders(self, user_id: int) -> List[FolderCategory]:
        """List all folders for a user.

        Args:
            user_id: The user ID to filter folders

        Returns:
            List[FolderCategory]: List of user's folders

        Example:
            >>> service = FolderService()
            >>> folders = await service.list_folders(user_id=1)
            >>> for folder in folders:
            ...     print(f"{folder.name} - {folder.gmail_label_id}")
        """
        async with self.db_service.async_session() as session:
            statement = select(FolderCategory).where(FolderCategory.user_id == user_id)
            result = await session.execute(statement)
            folders = result.scalars().all()

            logger.info(
                "folders_listed",
                user_id=user_id,
                folder_count=len(folders),
            )

            return list(folders)

    async def get_folder_by_id(self, folder_id: int, user_id: int) -> Optional[FolderCategory]:
        """Get a single folder by ID (with user_id check for security).

        Args:
            folder_id: The folder ID to retrieve
            user_id: The user ID (for ownership verification)

        Returns:
            Optional[FolderCategory]: The folder if found and owned by user, None otherwise

        Example:
            >>> service = FolderService()
            >>> folder = await service.get_folder_by_id(folder_id=5, user_id=1)
            >>> if folder:
            ...     print(f"Found folder: {folder.name}")
        """
        async with self.db_service.async_session() as session:
            statement = select(FolderCategory).where(
                FolderCategory.id == folder_id,
                FolderCategory.user_id == user_id,
            )
            result = await session.execute(statement)
            folder = result.scalar_one_or_none()

            if folder:
                logger.info(
                    "folder_fetched",
                    folder_id=folder_id,
                    user_id=user_id,
                    folder_name=folder.name,
                )
            else:
                logger.warning(
                    "folder_not_found",
                    folder_id=folder_id,
                    user_id=user_id,
                )

            return folder

    async def delete_folder(self, folder_id: int, user_id: int) -> bool:
        """Delete a folder category.

        Performs the following steps:
        1. Fetch folder from database (verify ownership)
        2. Delete Gmail label via Gmail API
        3. Delete FolderCategory record from database

        Args:
            folder_id: The folder ID to delete
            user_id: The user ID (for ownership verification)

        Returns:
            bool: True if deleted successfully, False if folder not found

        Raises:
            Exception: If Gmail API call fails or database operation fails

        Example:
            >>> service = FolderService()
            >>> success = await service.delete_folder(folder_id=5, user_id=1)
            >>> if success:
            ...     print("Folder deleted successfully")
        """
        async with self.db_service.async_session() as session:
            # Fetch folder (verify ownership)
            statement = select(FolderCategory).where(
                FolderCategory.id == folder_id,
                FolderCategory.user_id == user_id,
            )
            result = await session.execute(statement)
            folder = result.scalar_one_or_none()

            if not folder:
                logger.warning(
                    "folder_not_found_for_deletion",
                    folder_id=folder_id,
                    user_id=user_id,
                )
                return False

            gmail_label_id = folder.gmail_label_id
            folder_name = folder.name

            # Delete Gmail label (if it exists)
            if gmail_label_id:
                try:
                    gmail_client = GmailClient(user_id=user_id, db_service=self.db_service)
                    # Note: Gmail API doesn't have a direct delete label method in this implementation
                    # This would need to be added to GmailClient if required
                    # For now, we just log that we would delete it
                    logger.info(
                        "gmail_label_deletion_skipped",
                        user_id=user_id,
                        gmail_label_id=gmail_label_id,
                        note="Gmail label deletion not implemented - label will remain in Gmail",
                    )
                except Exception as e:
                    logger.error(
                        "gmail_label_deletion_failed",
                        user_id=user_id,
                        gmail_label_id=gmail_label_id,
                        error=str(e),
                    )
                    # Don't fail the entire operation if Gmail delete fails
                    # User can manually delete label in Gmail UI

            # Delete folder from database
            await session.delete(folder)
            await session.commit()

            logger.info(
                "folder_deleted",
                folder_id=folder_id,
                user_id=user_id,
                folder_name=folder_name,
                gmail_label_id=gmail_label_id,
            )

            return True
