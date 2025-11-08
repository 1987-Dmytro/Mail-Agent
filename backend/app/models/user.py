"""This file contains the user model for the application."""

from datetime import datetime, UTC
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

import bcrypt
from sqlalchemy import (
    DateTime,
    Text,
    func,
)
from sqlmodel import (
    Column,
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session
    from app.models.email import EmailProcessingQueue
    from app.models.folder_category import FolderCategory
    from app.models.linking_codes import LinkingCode
    from app.models.workflow_mapping import WorkflowMapping
    from app.models.notification_preferences import NotificationPreferences
    from app.models.approval_history import ApprovalHistory


class User(BaseModel, table=True):
    """User model for storing user accounts and Mail Agent integration data.

    Attributes:
        id: The primary key
        email: User's email (unique)
        hashed_password: Bcrypt hashed password (legacy field, may be removed in future)
        gmail_oauth_token: Encrypted Gmail OAuth access token (encrypted in Story 1.4)
        gmail_refresh_token: Encrypted Gmail OAuth refresh token (encrypted in Story 1.4)
        telegram_id: Telegram user ID for bot integration (Epic 2)
        telegram_username: Telegram username for display (Epic 2)
        is_active: Whether user account is active (soft delete pattern)
        onboarding_completed: Whether user finished Epic 4 onboarding wizard
        created_at: When the user was created (inherited from BaseModel)
        updated_at: When the user was last updated
        sessions: Relationship to user's chat sessions
        emails: Relationship to user's email processing queue
        folders: Relationship to user's folder categories (email organization)
    """

    __tablename__ = "users"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True, nullable=False)
    hashed_password: Optional[str] = Field(default=None)  # Legacy field, optional
    gmail_oauth_token: Optional[str] = Field(default=None, sa_column=Column(Text))
    gmail_refresh_token: Optional[str] = Field(default=None, sa_column=Column(Text))
    token_expiry: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    telegram_id: Optional[str] = Field(default=None, max_length=100, unique=True, index=True)
    telegram_username: Optional[str] = Field(default=None, max_length=100)
    telegram_linked_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    is_active: bool = Field(default=True)
    onboarding_completed: bool = Field(default=False)
    updated_at: datetime = Field(sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

    sessions: List["Session"] = Relationship(back_populates="user")
    emails: List["EmailProcessingQueue"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    folders: List["FolderCategory"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    linking_codes: List["LinkingCode"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    workflow_mappings: List["WorkflowMapping"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    notification_prefs: Optional["NotificationPreferences"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    approval_history: List["ApprovalHistory"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Avoid circular imports
from app.models.session import Session  # noqa: E402
from app.models.email import EmailProcessingQueue  # noqa: E402
from app.models.folder_category import FolderCategory  # noqa: E402
from app.models.linking_codes import LinkingCode  # noqa: E402
from app.models.workflow_mapping import WorkflowMapping  # noqa: E402
from app.models.notification_preferences import NotificationPreferences  # noqa: E402
from app.models.approval_history import ApprovalHistory  # noqa: E402
