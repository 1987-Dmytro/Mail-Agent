"""Email processing queue model for storing email metadata."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, String, Text, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class EmailProcessingQueue(BaseModel, table=True):
    """Email processing queue for tracking emails through the AI agent workflow.

    This model stores email metadata from Gmail for processing through:
    - Epic 1: Email monitoring and storage
    - Epic 2: AI classification and Telegram approval
    - Epic 3: RAG-based response generation

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        gmail_message_id: Unique Gmail message ID (for duplicate detection)
        gmail_thread_id: Gmail thread ID (for conversation grouping)
        sender: Email sender address
        subject: Email subject line
        received_at: When the email was received (from Gmail API)
        status: Processing status (pending, processing, approved, rejected, completed)
        classification: AI-determined email category (Epic 2)
        proposed_folder_id: Suggested folder for sorting (Epic 2)
        draft_response: AI-generated response draft (Epic 3)
        language: Detected language of email (Epic 3)
        priority_score: Email priority score (Epic 2)
        created_at: When record was created (inherited from BaseModel)
        updated_at: When record was last updated
        user: Relationship to User model
    """

    __tablename__ = "email_processing_queue"
    __table_args__ = (
        Index("ix_email_processing_queue_user_id", "user_id"),
        Index("ix_email_processing_queue_gmail_message_id", "gmail_message_id"),
        Index("ix_email_processing_queue_gmail_thread_id", "gmail_thread_id"),
        Index("ix_email_processing_queue_status", "status"),
    )

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    gmail_message_id: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    gmail_thread_id: str = Field(sa_column=Column(String(255), nullable=False))
    sender: str = Field(sa_column=Column(String(255), nullable=False))
    subject: Optional[str] = Field(default=None, sa_column=Column(Text))
    received_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: str = Field(default="pending", sa_column=Column(String(50), nullable=False))

    # Future fields for Epic 2 and Epic 3 (nullable until those epics are implemented)
    classification: Optional[str] = Field(default=None, max_length=50)
    proposed_folder_id: Optional[int] = Field(default=None)  # Will add FK in Epic 2 when folder_categories table exists
    draft_response: Optional[str] = Field(default=None, sa_column=Column(Text))
    language: Optional[str] = Field(default=None, max_length=10)
    priority_score: int = Field(default=0)

    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()))

    # Relationships
    user: "User" = Relationship(back_populates="emails")


# Avoid circular imports
from app.models.user import User  # noqa: E402
