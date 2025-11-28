"""WorkflowMapping model for LangGraph workflow tracking and Telegram callback reconnection."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.email import EmailProcessingQueue
    from app.models.user import User


class WorkflowMapping(BaseModel, table=True):
    """Maps email processing to LangGraph workflow instances and Telegram messages.

    This table enables cross-channel workflow pause/resume pattern:
    1. Workflow starts, generates unique thread_id
    2. WorkflowMapping created linking email_id → thread_id → telegram_message_id
    3. Workflow pauses at await_approval node, state saved to PostgreSQL
    4. User clicks button in Telegram (hours/days later)
    5. Callback handler uses email_id → lookup WorkflowMapping → get thread_id
    6. Workflow resumes from checkpoint using thread_id

    Attributes:
        id: The primary key
        email_id: Foreign key to email_processing_queue.id (unique, for workflow lookup)
        user_id: Foreign key to users.id (for per-user workflow queries)
        thread_id: LangGraph workflow instance ID (unique, format: email_{email_id}_{uuid})
        telegram_message_id: Telegram message ID (set after message sent, for message editing)
        workflow_state: Current workflow state (initialized, awaiting_approval, completed, error)
        created_at: Workflow creation timestamp (inherited from BaseModel)
        updated_at: Last state update timestamp
        email: Relationship to EmailProcessingQueue
        user: Relationship to User
    """

    __tablename__ = "workflow_mappings"

    id: int = Field(default=None, primary_key=True)
    email_id: int = Field(
        foreign_key="email_processing_queue.id",
        unique=True,
        nullable=False,
        index=True,
        ondelete="CASCADE"
    )
    user_id: int = Field(
        foreign_key="users.id",
        nullable=False,
        index=True,
        ondelete="CASCADE"
    )
    thread_id: str = Field(
        max_length=255,
        unique=True,
        nullable=False,
        index=True
    )
    telegram_message_id: Optional[str] = Field(
        default=None,
        max_length=100
    )
    workflow_state: str = Field(
        default="initialized",
        max_length=50,
        nullable=False
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now()
        )
    )

    # Indexes for fast lookup during callback reconnection
    __table_args__ = (
        Index('idx_workflow_mappings_thread_id', 'thread_id'),
        Index('idx_workflow_mappings_user_state', 'user_id', 'workflow_state'),
    )

    # Relationships
    email: Optional["EmailProcessingQueue"] = Relationship(back_populates="workflow_mappings")
    user: Optional["User"] = Relationship(back_populates="workflow_mappings")


# Avoid circular imports
from app.models.email import EmailProcessingQueue  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
