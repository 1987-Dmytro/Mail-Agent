"""Manual Notification Queue Model

This model stores failed Telegram notifications that require manual intervention.
Used as a fallback when automatic Telegram delivery fails after all retry attempts.

Epic 1 - Story 1.1: Fix send_telegram Error Handling
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlmodel import Field
from app.models.base import BaseModel
import enum


class NotificationStatus(str, enum.Enum):
    """Status of manual notification task"""
    PENDING = "pending"  # Waiting for manual retry
    RETRYING = "retrying"  # Currently being retried
    SENT = "sent"  # Successfully sent after manual intervention
    FAILED = "failed"  # Permanently failed


class ManualNotification(BaseModel, table=True):
    """Queue for Telegram notifications that failed automatic delivery.

    When Telegram API is unreachable or messages consistently fail,
    notifications are queued here for manual intervention or later retry.

    Attributes:
        id: Primary key
        email_id: Reference to EmailProcessingQueue.id
        telegram_id: User's Telegram chat ID
        message_text: Original message text to send
        buttons_json: JSON serialized inline keyboard buttons
        error_type: Type of error that caused fallback (e.g., 'TelegramAPIError')
        error_message: Detailed error message
        retry_count: Number of retry attempts made
        status: Current status (pending/retrying/sent/failed)
        created_at: When notification was queued (inherited from BaseModel)
        last_retry_at: Last retry attempt timestamp
        sent_at: When successfully sent (if applicable)
    """

    __tablename__ = "manual_notifications"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    email_id: int = Field(
        sa_column=Column(Integer, nullable=False, index=True)
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

    # Error tracking
    error_type: str = Field(
        max_length=100,
        sa_column=Column(String(100), nullable=False)
    )
    error_message: str = Field(
        sa_column=Column(Text, nullable=False)
    )
    retry_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False)
    )

    # Status tracking
    status: str = Field(
        default=NotificationStatus.PENDING.value,
        max_length=20,
        sa_column=Column(String(20), nullable=False, index=True)
    )

    # Timestamps (created_at inherited from BaseModel)
    last_retry_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    sent_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    def __repr__(self) -> str:
        return (
            f"<ManualNotification(id={self.id}, email_id={self.email_id}, "
            f"status={self.status}, retry_count={self.retry_count})>"
        )
