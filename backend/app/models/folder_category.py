"""FolderCategory model for user-defined email organization folders."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class FolderCategory(BaseModel, table=True):
    """FolderCategory model for storing user-defined email organization folders.

    Each folder corresponds to a Gmail label and is used for AI-powered email classification
    in Epic 2. Keywords help guide classification, and colors provide visual differentiation
    in the UI (Epic 4).

    Attributes:
        id: The primary key
        user_id: Foreign key to users table (cascade delete)
        name: Folder display name (max 100 chars, unique per user)
        gmail_label_id: Gmail's internal label ID (e.g., "Label_123")
        keywords: List of keywords for AI classification hints (Epic 2)
        color: Hex color code for UI display (e.g., "#FF5733")
        is_default: Whether this is a default system folder
        created_at: When the folder was created (inherited from BaseModel)
        updated_at: When the folder was last updated
        user: Relationship to User model
    """

    __tablename__ = "folder_categories"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(max_length=100, nullable=False)
    gmail_label_id: Optional[str] = Field(default=None, max_length=100, index=True)
    keywords: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    color: Optional[str] = Field(default=None, max_length=7)  # Hex color codes (#FF5733)
    is_default: bool = Field(default=False)
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )

    # Relationships
    user: "User" = Relationship(back_populates="folders")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_folder_name"),
    )


# Avoid circular imports
from app.models.user import User  # noqa: E402
