"""Email processing queue model for storing email metadata."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.folder_category import FolderCategory
    from app.models.user import User
    from app.models.workflow_mapping import WorkflowMapping


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
        classification: AI-determined email category ("sort_only" or "needs_response")
        proposed_folder_id: Foreign key to folder_categories (suggested folder for sorting)
        classification_reasoning: AI reasoning for transparency (max 300 chars)
        priority_score: Email priority score 0-100 (Epic 2)
        is_priority: Boolean flag for priority_score >= 70 (triggers immediate notification)
        draft_response: AI-generated response draft (Epic 3)
        language: Detected language of email (Epic 3)
        detected_language: Detected language code (ru/uk/en/de) from Story 3.5
        tone: Detected tone (formal/professional/casual) from Story 3.6
        created_at: When record was created (inherited from BaseModel)
        updated_at: When record was last updated
        user: Relationship to User model
        proposed_folder: Relationship to FolderCategory model (suggested folder)
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

    # Epic 2: AI Classification fields
    classification: Optional[str] = Field(default=None, sa_column=Column(String(50)))  # "sort_only" or "needs_response"
    proposed_folder_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("folder_categories.id", ondelete="SET NULL"), nullable=True)
    )
    classification_reasoning: Optional[str] = Field(default=None, sa_column=Column(Text))
    priority_score: int = Field(default=0)
    is_priority: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))

    # Epic 3: RAG Response fields
    draft_response: Optional[str] = Field(default=None, sa_column=Column(Text))
    language: Optional[str] = Field(default=None, max_length=10)
    detected_language: Optional[str] = Field(default=None, sa_column=Column(String(5)))  # Story 3.5: Language detection (ru, uk, en, de)
    tone: Optional[str] = Field(default=None, sa_column=Column(String(20)))  # Story 3.6: Tone detection (formal, professional, casual)

    # Story 2.11: Error handling and recovery fields
    error_type: Optional[str] = Field(default=None, sa_column=Column(String(100)))  # e.g., "gmail_api_failure", "telegram_send_failure"
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))  # Full error message from last failed attempt
    error_timestamp: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))  # When error status was set
    retry_count: int = Field(default=0)  # Number of retry attempts made
    dlq_reason: Optional[str] = Field(default=None, sa_column=Column(Text))  # Reason for moving to dead letter queue (after MAX_RETRIES exhausted)

    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()))

    # Relationships
    user: "User" = Relationship(back_populates="emails")
    proposed_folder: Optional["FolderCategory"] = Relationship()
    workflow_mappings: Optional["WorkflowMapping"] = Relationship(back_populates="email")


# Avoid circular imports
from app.models.user import User  # noqa: E402
from app.models.workflow_mapping import WorkflowMapping  # noqa: E402
