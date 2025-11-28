"""Linking codes model for Telegram account linking."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class LinkingCode(BaseModel, table=True):
    """Temporary linking code for secure Telegram account association.

    Attributes:
        id: The primary key
        code: 6-character alphanumeric code (A-Z, 0-9)
        user_id: Foreign key to users table
        used: Whether the code has been used for linking
        expires_at: When the code expires (15 minutes from creation)
        created_at: When the code was created (inherited from BaseModel)
        user: Relationship to the User who owns this linking code
    """

    __tablename__ = "linking_codes"

    id: int = Field(default=None, primary_key=True)
    code: str = Field(max_length=6, unique=True, index=True, nullable=False)
    user_id: int = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    used: bool = Field(default=False, nullable=False)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    # Relationship
    user: Optional["User"] = Relationship(back_populates="linking_codes")


# Avoid circular imports
from app.models.user import User  # noqa: E402, F401
