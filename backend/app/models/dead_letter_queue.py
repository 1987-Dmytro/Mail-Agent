"""Dead Letter Queue model for failed Gmail actions (Story 1.3).

This model defines the DeadLetterQueue model for tracking Gmail API operations
that failed after all retry attempts were exhausted. Used for manual intervention
and debugging persistent failures.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, DateTime, Integer, String, Text, JSON, func
from sqlmodel import Field, Relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.email import EmailProcessingQueue


class DeadLetterQueue(BaseModel, table=True):
    """Dead Letter Queue for failed Gmail actions (Story 1.3).

    Records Gmail API operations that failed after all retry attempts (3 retries
    with exponential backoff). These records require manual intervention to resolve
    the inconsistency between Gmail and database state.

    Attributes:
        id: Primary key
        created_at: Timestamp when DLQ record was created
        email_queue_id: Foreign key to EmailProcessingQueue
        operation_type: Type of operation that failed (e.g., "apply_label", "send_email")
        gmail_message_id: Gmail message ID for the operation
        label_id: Gmail label ID that was supposed to be applied (for apply_label operations)
        error_type: Type of error (e.g., "GmailAPIError", "HttpError", "Timeout")
        error_message: Detailed error message from the failed operation
        retry_count: Number of retry attempts made (always 3 for DLQ entries)
        last_retry_at: Timestamp of the last retry attempt
        context_json: Additional context as JSON string (state snapshot, user_id, etc.)
        resolved: Whether this DLQ entry has been manually resolved
        resolved_at: Timestamp when the issue was resolved
        resolution_notes: Manual intervention notes

    Relationships:
        email_queue: The EmailProcessingQueue record that failed
    """

    __tablename__ = "dead_letter_queue"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )

    # Foreign key to email that failed
    email_queue_id: int = Field(foreign_key="email_processing_queue.id", index=True)

    # Operation details
    operation_type: str = Field(max_length=50)  # "apply_label", "send_email", etc.
    gmail_message_id: str = Field(index=True)
    label_id: Optional[str] = Field(default=None)  # Gmail label ID (for apply_label operations)

    # Error details
    error_type: str = Field(max_length=100)  # Exception type name
    error_message: str = Field(sa_column=Column(Text))  # Full error message
    retry_count: int = Field(default=3)  # Always 3 for DLQ
    last_retry_at: datetime

    # Additional context (JSON stored as text)
    context_json: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Resolution tracking
    resolved: int = Field(default=0)  # 0 = unresolved, 1 = resolved
    resolved_at: Optional[datetime] = Field(default=None)
    resolution_notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Relationships
    email_queue: Optional["EmailProcessingQueue"] = Relationship(back_populates="dead_letter_entries")
