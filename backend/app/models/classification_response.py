"""
Classification Response Model

Pydantic model for AI email classification responses from Gemini LLM.
Defines the structured JSON schema that the LLM must return when classifying emails.

This model is used for:
1. JSON schema validation of Gemini API responses
2. Prompt engineering (schema specification included in prompt)
3. Type safety in classification service (Story 2.3)
4. Approval history tracking (Story 2.10)

Version: 1.0
Created: 2025-11-07
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ClassificationResponse(BaseModel):
    """
    Email classification response from AI with folder suggestion and reasoning.

    The LLM analyzes email metadata (sender, subject, body) and user-defined folder
    categories, then returns this structured response with:
    - Suggested folder category (must match user's folder names)
    - Brief reasoning (1-2 sentences explaining the classification decision)
    - Optional priority score (0-100 scale, used by priority detection in Story 2.9)
    - Optional confidence level (0.0-1.0 scale, for accuracy tracking)

    Example JSON Response:
        {
            "suggested_folder": "Government",
            "reasoning": "Email from Finanzamt (Tax Office) regarding tax documents deadline",
            "priority_score": 85,
            "confidence": 0.92
        }
    """

    suggested_folder: str = Field(
        ...,
        description="Name of the folder category to sort email into. Must exactly match one of the user's folder category names.",
        min_length=1,
        max_length=100
    )

    reasoning: str = Field(
        ...,
        description="1-2 sentence explanation for classification decision. Explains why this folder was chosen based on sender, subject, or content.",
        min_length=10,
        max_length=300  # Telegram message limit consideration
    )

    priority_score: Optional[int] = Field(
        default=None,
        description="Priority score (0-100). Higher scores indicate more urgent/important emails. Government emails: 80-100, Clients: 50-70, Newsletters: 0-20.",
        ge=0,  # Greater than or equal to 0
        le=100  # Less than or equal to 100
    )

    confidence: Optional[float] = Field(
        default=None,
        description="Confidence level (0.0-1.0). How certain the AI is about this classification. Values <0.7 indicate uncertainty and suggest manual review.",
        ge=0.0,  # Greater than or equal to 0.0
        le=1.0  # Less than or equal to 1.0
    )

    @field_validator('reasoning')
    @classmethod
    def validate_reasoning_length(cls, v: str) -> str:
        """
        Validate reasoning is concise (max 300 characters for Telegram limit).

        Raises:
            ValueError: If reasoning exceeds 300 characters
        """
        if len(v) > 300:
            raise ValueError(f"Reasoning must be max 300 characters, got {len(v)}")
        return v

    @field_validator('suggested_folder')
    @classmethod
    def validate_folder_not_empty(cls, v: str) -> str:
        """
        Validate suggested_folder is not empty or whitespace-only.

        Raises:
            ValueError: If folder name is empty or only whitespace
        """
        if not v or not v.strip():
            raise ValueError("suggested_folder cannot be empty")
        return v.strip()

    @field_validator('priority_score')
    @classmethod
    def validate_priority_score_range(cls, v: Optional[int]) -> Optional[int]:
        """
        Validate priority_score is within 0-100 range if provided.

        Raises:
            ValueError: If priority_score is outside 0-100 range
        """
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"priority_score must be between 0 and 100, got {v}")
        return v

    @field_validator('confidence')
    @classmethod
    def validate_confidence_range(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate confidence is within 0.0-1.0 range if provided.

        Raises:
            ValueError: If confidence is outside 0.0-1.0 range
        """
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {v}")
        return v

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "suggested_folder": "Government",
                "reasoning": "Official communication from Finanzamt (Tax Office) regarding tax return deadline",
                "priority_score": 85,
                "confidence": 0.95
            }
        }

    def to_dict(self):
        """
        Convert model to dictionary, excluding None values for optional fields.

        Returns:
            Dict with only populated fields (required + optional fields that are not None)
        """
        return self.model_dump(exclude_none=True)
