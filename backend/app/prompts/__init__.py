"""
Prompt templates for AI email operations.

This module contains prompt engineering templates for various AI operations:
- classification_prompt: Email classification into user-defined folder categories
- response_generation: Email response generation with tone detection and multilingual support
"""

from .classification_prompt import (
    build_classification_prompt,
    CLASSIFICATION_PROMPT_VERSION,
)
from .response_generation import (
    RESPONSE_PROMPT_TEMPLATE,
    GREETING_EXAMPLES,
    CLOSING_EXAMPLES,
    LANGUAGE_NAMES,
    format_response_prompt,
)

__all__ = [
    "build_classification_prompt",
    "CLASSIFICATION_PROMPT_VERSION",
    "RESPONSE_PROMPT_TEMPLATE",
    "GREETING_EXAMPLES",
    "CLOSING_EXAMPLES",
    "LANGUAGE_NAMES",
    "format_response_prompt",
]
