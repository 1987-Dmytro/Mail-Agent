"""
Prompt templates for AI email classification.

This module contains prompt engineering templates for various AI operations:
- classification_prompt: Email classification into user-defined folder categories
"""

from .classification_prompt import (
    build_classification_prompt,
    CLASSIFICATION_PROMPT_VERSION,
)

__all__ = [
    "build_classification_prompt",
    "CLASSIFICATION_PROMPT_VERSION",
]
