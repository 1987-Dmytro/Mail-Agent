"""Batch Notification Queue Model

This model stores non-priority email notifications for daily batch sending.
Instead of sending immediately, non-priority emails are queued and sent once per day.

Sprint 001 - Story 2.3: Implement Batching for Non-Priority Emails
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, String, Text, Date, func
from sqlmodel import Field
from app.models.base import BaseModel
import enum


class BatchNotificationStatus(str, enum.Enum):
    """Status of batched notification"""
    PENDING = "pending"  # Waiting to be sent in batch
    SENT = "sent"  # Successfully sent in digest
    FAILED = "failed"  # Failed to send


class BatchNotificationQueue(BaseModel, table=True):
    """Queue for non-priority email notifications to be sent in daily batches.

    Non-priority emails (priority_score < 70) are queued here instead of
    being sent immediately. A daily digest task sends all pending notifications
    once per day, reducing notification noise for users.

    Attributes:
        id: Primary key
        user_id: User ID who owns this email
        email_id: Reference to EmailProcessingQueue.id
        telegram_id: User's Telegram chat ID
        message_text: Formatted message text for the notification
        buttons_json: JSON serialized inline keyboard buttons
        priority_score: Original priority score of the email
        scheduled_for: Date when this notification should be sent (default: today)
        status: Current status (pending/sent/failed)
        created_at: When notification was queued (inherited from BaseModel)
        sent_at: When digest containing this notification was sent
    """

    __tablename__ = "batch_notification_queue"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    user_id: int = Field(
        sa_column=Column(Integer, nullable=False, index=True)
    )
    email_id: int = Field(
        sa_column=Column(Integer, nullable=False, index=True, unique=True)
    )
    telegram_id: str = Field(
        max_length=50,
        sa_column=Column(String(50), nullable=False)
    )
    message_text: str = Field(
        sa_column=Column(Text, nullable=False)
    )
    buttons_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    priority_score: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False)
    )

    # Scheduling
    scheduled_for: date = Field(
        default_factory=date.today,
        sa_column=Column(Date, nullable=False, index=True)
    )

    # Status tracking
    status: str = Field(
        default=BatchNotificationStatus.PENDING.value,
        max_length=20,
        sa_column=Column(String(20), nullable=False, index=True)
    )

    # Timestamps (created_at inherited from BaseModel)
    sent_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    def __repr__(self) -> str:
        return (
            f"<BatchNotificationQueue(id={self.id}, user_id={self.user_id}, "
            f"email_id={self.email_id}, status={self.status}, "
            f"scheduled_for={self.scheduled_for})>"
        )
