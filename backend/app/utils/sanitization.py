"""This file contains the sanitization utilities for the application."""

import html
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)


def sanitize_string(value: str) -> str:
    """Sanitize a string to prevent XSS and other injection attacks.

    Args:
        value: The string to sanitize

    Returns:
        str: The sanitized string
    """
    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # HTML escape to prevent XSS
    value = html.escape(value)

    # Remove any script tags that might have been escaped
    value = re.sub(r"&lt;script.*?&gt;.*?&lt;/script&gt;", "", value, flags=re.DOTALL)

    # Remove null bytes
    value = value.replace("\0", "")

    return value


def sanitize_email(email: str) -> str:
    """Sanitize an email address.

    Args:
        email: The email address to sanitize

    Returns:
        str: The sanitized email address
    """
    # Basic sanitization
    email = sanitize_string(email)

    # Ensure email format (simple check)
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.

    Args:
        data: The dictionary to sanitize

    Returns:
        Dict[str, Any]: The sanitized dictionary
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_list(data: List[Any]) -> List[Any]:
    """Recursively sanitize all string values in a list.

    Args:
        data: The list to sanitize

    Returns:
        List[Any]: The sanitized list
    """
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            sanitized.append(item)
    return sanitized


def validate_password_strength(password: str) -> bool:
    """Validate password strength.

    Args:
        password: The password to validate

    Returns:
        bool: Whether the password is strong enough

    Raises:
        ValueError: If the password is not strong enough with reason
    """
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters long")

    return True


def sanitize_oauth_parameter(value: str, param_name: str = "parameter", max_length: int = 2048) -> str:
    """Sanitize OAuth parameters (code, state) to prevent injection attacks.

    OAuth parameters should only contain alphanumeric characters, hyphens, underscores,
    and URL-safe base64 characters.

    Args:
        value: The OAuth parameter value to sanitize
        param_name: Name of the parameter (for error messages)
        max_length: Maximum allowed length for the parameter

    Returns:
        str: The sanitized OAuth parameter

    Raises:
        ValueError: If the parameter contains invalid characters or exceeds max length
    """
    if not isinstance(value, str):
        raise ValueError(f"{param_name} must be a string")

    # Remove null bytes
    value = value.replace("\0", "")

    # Check length
    if len(value) > max_length:
        raise ValueError(f"{param_name} exceeds maximum length of {max_length}")

    if len(value) == 0:
        raise ValueError(f"{param_name} cannot be empty")

    # OAuth parameters should only contain alphanumeric, hyphens, underscores, and URL-safe characters
    # Allow: a-z, A-Z, 0-9, -, _, ., ~, %, / (Google OAuth codes often start with "4/")
    if not re.match(r"^[a-zA-Z0-9\-_.~%/]+$", value):
        raise ValueError(f"{param_name} contains invalid characters")

    return value
