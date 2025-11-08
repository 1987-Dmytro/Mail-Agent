"""Notification preferences model for batch notification timing and user preferences."""

from datetime import datetime, time, UTC
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Time, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class NotificationPreferences(BaseModel, table=True):
    """User notification settings for batch timing.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table (one-to-one relationship)
        batch_enabled: Whether daily batch notifications are enabled
        batch_time: Preferred time for batch notifications (default: 18:00 / 6 PM)
        priority_immediate: Whether priority emails bypass batching (default: True)
        quiet_hours_start: Optional start time for quiet hours (e.g., 22:00)
        quiet_hours_end: Optional end time for quiet hours (e.g., 08:00)
        timezone: User timezone for scheduling (default: UTC)
        created_at: When preferences were created (inherited from BaseModel)
        updated_at: When preferences were last updated
        user: Relationship to the User who owns these preferences
    """

    __tablename__ = "notification_preferences"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    batch_enabled: bool = Field(default=True)
    batch_time: time = Field(
        default=time(18, 0),
        sa_column=Column(Time, nullable=False, server_default="18:00:00")
    )
    priority_immediate: bool = Field(default=True)
    quiet_hours_start: Optional[time] = Field(
        default=None,
        sa_column=Column(Time, nullable=True)
    )
    quiet_hours_end: Optional[time] = Field(
        default=None,
        sa_column=Column(Time, nullable=True)
    )
    timezone: str = Field(default="UTC", max_length=50)
    updated_at: datetime = Field(
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()}
    )

    # Relationships
    user: "User" = Relationship(back_populates="notification_prefs")


# Avoid circular imports
from app.models.user import User  # noqa: E402
