"""Telegram account linking service for generating and validating linking codes."""

import secrets
import string
from datetime import datetime, timedelta, UTC
from typing import Any

import structlog
from sqlmodel import Session, select

from app.models.linking_codes import LinkingCode
from app.models.user import User

logger = structlog.get_logger(__name__)


def generate_linking_code(user_id: int, db: Session) -> str:
    """Generate unique 6-digit alphanumeric linking code for Telegram account connection.

    Args:
        user_id: The user ID to associate with the linking code
        db: Database session

    Returns:
        str: 6-character alphanumeric code (uppercase A-Z, 0-9)

    Raises:
        ValueError: If code generation fails after multiple attempts
    """
    # Generate random code using uppercase letters and digits only
    # (avoid lowercase to prevent confusion like O vs 0, l vs 1)
    max_attempts = 10
    for attempt in range(max_attempts):
        code = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

        # Check for uniqueness (extremely rare to have collision)
        existing_code = db.exec(
            select(LinkingCode).where(LinkingCode.code == code)
        ).first()

        if not existing_code:
            # Create LinkingCode record with 15-minute expiration
            expires_at = datetime.now(UTC) + timedelta(minutes=15)
            linking_code = LinkingCode(
                code=code,
                user_id=user_id,
                used=False,
                expires_at=expires_at
            )
            db.add(linking_code)
            db.commit()
            db.refresh(linking_code)

            logger.info(
                "linking_code_generated",
                user_id=user_id,
                code=code,
                expires_at=expires_at.isoformat()
            )

            return code

    # This should never happen (probability < 1 in 2 billion)
    logger.error(
        "linking_code_generation_failed",
        user_id=user_id,
        attempts=max_attempts,
        reason="too_many_collisions"
    )
    raise ValueError(f"Failed to generate unique code after {max_attempts} attempts")


def link_telegram_account(
    telegram_id: str,
    telegram_username: str | None,
    code: str,
    db: Session
) -> dict[str, Any]:
    """Validate linking code and associate telegram_id with user account.

    Args:
        telegram_id: Telegram user ID (from update.effective_user.id)
        telegram_username: Telegram username (optional, from update.effective_user.username)
        code: 6-character linking code to validate
        db: Database session

    Returns:
        dict: Result with 'success' (bool) and either 'message' or 'error' key
            Success: {"success": True, "message": "..."}
            Failure: {"success": False, "error": "..."}
    """
    try:
        # Normalize code to uppercase for case-insensitive matching
        code = code.upper()

        # Find linking code
        code_record = db.exec(
            select(LinkingCode).where(LinkingCode.code == code)
        ).first()

        # Validation: Code not found
        if not code_record:
            logger.warning(
                "linking_code_not_found",
                telegram_id=telegram_id,
                code=code
            )
            return {
                "success": False,
                "error": "Invalid linking code. Please check and try again."
            }

        # Validation: Code already used (AC #7)
        if code_record.used:
            logger.warning(
                "linking_code_already_used",
                telegram_id=telegram_id,
                code=code,
                user_id=code_record.user_id
            )
            return {
                "success": False,
                "error": "This code has already been used. Generate a new code."
            }

        # Validation: Code expired (AC #6)
        # Handle timezone-aware comparison (PostgreSQL) and timezone-naive (SQLite tests)
        expires_at = code_record.expires_at
        if expires_at.tzinfo is None:
            # SQLite returns naive datetimes - assume UTC
            expires_at = expires_at.replace(tzinfo=UTC)

        if datetime.now(UTC) > expires_at:
            logger.warning(
                "linking_code_expired",
                telegram_id=telegram_id,
                code=code,
                expires_at=code_record.expires_at.isoformat()
            )
            return {
                "success": False,
                "error": "This code has expired. Generate a new code (codes expire after 15 minutes)."
            }

        # Check if telegram_id already linked to another user
        existing_user = db.exec(
            select(User).where(User.telegram_id == telegram_id)
        ).first()

        if existing_user and existing_user.id != code_record.user_id:
            logger.warning(
                "telegram_id_already_linked",
                telegram_id=telegram_id,
                existing_user_id=existing_user.id,
                attempted_user_id=code_record.user_id
            )
            return {
                "success": False,
                "error": "This Telegram account is already linked to another Mail Agent account."
            }

        # Link telegram_id to user (AC #5, #9)
        user = db.exec(
            select(User).where(User.id == code_record.user_id)
        ).first()

        if not user:
            logger.error(
                "user_not_found_for_linking_code",
                user_id=code_record.user_id,
                code=code
            )
            return {
                "success": False,
                "error": "An error occurred during linking. Please try again."
            }

        # Update user with Telegram information
        user.telegram_id = telegram_id
        user.telegram_username = telegram_username
        user.telegram_linked_at = datetime.now(UTC)

        # Mark code as used
        code_record.used = True

        db.commit()

        logger.info(
            "telegram_account_linked",
            user_id=user.id,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            code=code
        )

        # Success message (AC #8)
        return {
            "success": True,
            "message": (
                "✅ Your Telegram account has been linked successfully!\n\n"
                "You'll receive email notifications here. "
                "You can start approving sorting proposals and response drafts right from this chat."
            )
        }

    except Exception as e:
        db.rollback()
        logger.error(
            "telegram_linking_failed",
            telegram_id=telegram_id,
            code=code,
            error=str(e),
            exc_info=True
        )
        return {
            "success": False,
            "error": "An error occurred during linking. Please try again."
        }
