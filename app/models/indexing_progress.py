"""IndexingProgress model for tracking email history indexing jobs."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class IndexingStatus(str, Enum):
    """Status enum for indexing progress tracking."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class IndexingProgress(BaseModel, table=True):
    """Model for tracking email indexing progress per user.

    This model tracks the progress of email history indexing jobs for each user,
    enabling resumable indexing after interruption and progress visibility.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table (one indexing job per user)
        total_emails: Total number of emails to index
        processed_count: Number of emails processed so far
        status: Current indexing status (in_progress/completed/failed/paused)
        error_message: Error details if status is failed
        last_processed_message_id: Gmail message ID of last processed email (checkpoint)
        started_at: When indexing job started (inherited from BaseModel as created_at)
        completed_at: When indexing job completed (null if in progress)
        user: Relationship to User model
    """

    __tablename__ = "indexing_progress"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_indexing_progress_user_id"),
    )

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    total_emails: int = Field(default=0, nullable=False)
    processed_count: int = Field(default=0, nullable=False)
    status: IndexingStatus = Field(default=IndexingStatus.IN_PROGRESS, nullable=False)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    last_processed_message_id: Optional[str] = Field(default=None, max_length=255)
    completed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Relationship
    user: "User" = Relationship(back_populates="indexing_progress")


# Avoid circular imports
from app.models.user import User  # noqa: E402
