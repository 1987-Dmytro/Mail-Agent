"""Email service for querying and managing EmailProcessingQueue records."""

from typing import List, Optional

import structlog
from sqlmodel import select

from app.models.email import EmailProcessingQueue
from app.services.database import DatabaseService, database_service

logger = structlog.get_logger(__name__)


class EmailService:
    """Service for managing email processing queue operations.

    Provides query methods for fetching emails by status, updating email status,
    and retrieving emails by Gmail message ID for duplicate detection.
    """

    def __init__(self, db_service: DatabaseService = None):
        """Initialize EmailService with database service.

        Args:
            db_service: DatabaseService instance (defaults to global database_service)
        """
        self.db_service = db_service or database_service

    async def get_emails_by_status(
        self, user_id: int, status: str
    ) -> List[EmailProcessingQueue]:
        """Fetch all emails for user with given status.

        Args:
            user_id: The user ID to filter emails
            status: The status to filter by (e.g., 'pending', 'processing', 'approved')

        Returns:
            List[EmailProcessingQueue]: List of emails matching the status

        Example:
            >>> service = EmailService()
            >>> pending_emails = await service.get_emails_by_status(user_id=1, status="pending")
        """
        async with self.db_service.async_session() as session:
            statement = select(EmailProcessingQueue).where(
                EmailProcessingQueue.user_id == user_id,
                EmailProcessingQueue.status == status,
            )
            result = await session.execute(statement)
            emails = result.scalars().all()

            logger.info(
                "emails_fetched_by_status",
                user_id=user_id,
                status=status,
                count=len(emails),
            )

            return list(emails)

    async def get_pending_emails(self, user_id: int) -> List[EmailProcessingQueue]:
        """Convenience method to fetch pending emails for a user.

        This is a wrapper around get_emails_by_status for the common case of
        fetching emails with status="pending".

        Args:
            user_id: The user ID to filter emails

        Returns:
            List[EmailProcessingQueue]: List of pending emails

        Example:
            >>> service = EmailService()
            >>> pending_emails = await service.get_pending_emails(user_id=1)
        """
        return await self.get_emails_by_status(user_id, "pending")

    async def get_email_by_message_id(
        self, gmail_message_id: str
    ) -> Optional[EmailProcessingQueue]:
        """Find email by Gmail message ID (for duplicate detection).

        Args:
            gmail_message_id: The Gmail message ID to search for

        Returns:
            Optional[EmailProcessingQueue]: The email record if found, None otherwise

        Example:
            >>> service = EmailService()
            >>> email = await service.get_email_by_message_id("18abc123def456")
            >>> if email:
            >>>     print(f"Email already exists with status: {email.status}")
        """
        async with self.db_service.async_session() as session:
            statement = select(EmailProcessingQueue).where(
                EmailProcessingQueue.gmail_message_id == gmail_message_id
            )
            result = await session.execute(statement)
            email = result.scalar_one_or_none()

            if email:
                logger.info(
                    "email_found_by_message_id",
                    gmail_message_id=gmail_message_id,
                    email_id=email.id,
                    status=email.status,
                )
            else:
                logger.info(
                    "email_not_found_by_message_id", gmail_message_id=gmail_message_id
                )

            return email

    async def update_email_status(
        self, email_id: int, new_status: str
    ) -> EmailProcessingQueue:
        """Update email status (e.g., pending → processing → approved → completed).

        Args:
            email_id: The ID of the email to update
            new_status: The new status value

        Returns:
            EmailProcessingQueue: The updated email record

        Raises:
            ValueError: If email with given ID not found

        Example:
            >>> service = EmailService()
            >>> email = await service.update_email_status(email_id=123, new_status="processing")
            >>> print(f"Email status updated to: {email.status}")
        """
        async with self.db_service.async_session() as session:
            statement = select(EmailProcessingQueue).where(
                EmailProcessingQueue.id == email_id
            )
            result = await session.execute(statement)
            email = result.scalar_one_or_none()

            if not email:
                logger.error("email_not_found_for_status_update", email_id=email_id)
                raise ValueError(f"Email with ID {email_id} not found")

            old_status = email.status
            email.status = new_status
            await session.commit()
            await session.refresh(email)

            logger.info(
                "email_status_updated",
                email_id=email_id,
                old_status=old_status,
                new_status=new_status,
                user_id=email.user_id,
            )

            return email
