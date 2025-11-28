"""Base models and common imports for all models."""

from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import func
from sqlmodel import Field, SQLModel, Relationship


class BaseModel(SQLModel):
    """Base model with common fields."""

    created_at: datetime = Field(sa_column_kwargs={"server_default": func.now()})
