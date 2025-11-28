"""Database models for prompt version tracking and management.

This module provides the PromptVersion model for storing and versioning
prompt templates used in email response generation. Enables:
- A/B testing of different prompt variations
- Rollback to previous prompt versions
- Tracking which prompt version generated each response
- Refinement based on user feedback

Architecture: Supports future prompt optimization workflows.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, JSON, Column
from pydantic import ConfigDict
import structlog


logger = structlog.get_logger(__name__)


class PromptVersion(SQLModel, table=True):
    """Database model for storing versioned prompt templates.

    Each prompt template (e.g., "response_generation") can have multiple versions
    tracked over time, enabling experimentation, refinement, and rollback.

    Attributes:
        id: Primary key
        template_name: Name of the prompt template (e.g., "response_generation")
        template_content: Full prompt template string with placeholders
        version: Semantic version string (e.g., "1.0.0", "1.1.0")
        created_at: Timestamp when this version was created
        parameters: JSON field for additional metadata (token_budget, constraints, etc.)
        is_active: Whether this version is currently in use (only one active per template_name)

    Examples:
        >>> prompt_v1 = PromptVersion(
        ...     template_name="response_generation",
        ...     template_content="...",
        ...     version="1.0.0",
        ...     parameters={"token_budget": 6500}
        ... )
    """

    __tablename__ = "prompt_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_name: str = Field(index=True, description="Name of the prompt template")
    template_content: str = Field(description="Full prompt template string")
    version: str = Field(description="Semantic version (e.g., '1.0.0')")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata (token_budget, constraints, etc.)",
    )
    is_active: bool = Field(
        default=False, description="Whether this version is currently active"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template_name": "response_generation",
                "template_content": "You are an AI email assistant...",
                "version": "1.0.0",
                "parameters": {"token_budget": 6500, "max_paragraphs": 3},
                "is_active": True,
            }
        }
    )
