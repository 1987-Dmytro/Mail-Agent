"""Gmail OAuth token refresh utilities.

This module provides functions for automatically refreshing expired Gmail OAuth
access tokens using the refresh token.
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.config import settings
from app.core.encryption import (
    decrypt_token,
    encrypt_token,
)
from app.core.logging import logger
from app.services.database import (
    DatabaseService,
    database_service,
)


async def refresh_access_token(
    user_id: int,
    db_service: DatabaseService = None,
) -> str:
    """Refresh expired access token using refresh token.

    This function automatically refreshes the Gmail OAuth access token when it expires,
    using the stored refresh token. The new access token is encrypted and stored back
    in the database.

    Args:
        user_id: The ID of the user whose token needs refreshing
        db_service: Database service (optional, uses singleton if not provided)

    Returns:
        str: The new (decrypted) access token

    Raises:
        ValueError: If user not found or refresh token missing
        Exception: If token refresh fails (invalid refresh token, network error)
    """
    # Use provided service or fall back to singleton
    if db_service is None:
        db_service = database_service

    try:
        # Load user from database
        user = await db_service.get_user(user_id)
        if not user:
            logger.error("user_not_found_for_token_refresh", user_id=user_id)
            raise ValueError(f"User {user_id} not found")

        if not user.gmail_refresh_token:
            logger.error("refresh_token_missing", user_id=user_id)
            raise ValueError(f"No refresh token found for user {user_id}")

        # Decrypt refresh token
        refresh_token = decrypt_token(user.gmail_refresh_token)

        # Create credentials object with refresh token
        credentials = Credentials(
            token=None,  # Expired access token
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
        )

        # Refresh the access token
        request = Request()
        credentials.refresh(request)

        # Get the new access token
        new_access_token = credentials.token

        # Encrypt and save new access token
        encrypted_token = encrypt_token(new_access_token)
        user.gmail_oauth_token = encrypted_token

        # Update token expiry if available
        if hasattr(user, "token_expiry") and credentials.expiry:
            user.token_expiry = credentials.expiry

        # Save to database
        await db_service.update_user(user)

        logger.info("access_token_refreshed", user_id=user_id)

        return new_access_token

    except ValueError:
        raise
    except Exception as e:
        logger.error("token_refresh_failed", user_id=user_id, error=str(e), exc_info=True)
        raise Exception(f"Failed to refresh access token: {str(e)}")


async def get_valid_gmail_credentials(
    user_id: int,
    db_service: DatabaseService = None,
) -> Credentials:
    """Get valid Gmail credentials for a user, refreshing if necessary.

    This is a convenience function that checks if the access token needs refreshing
    and automatically refreshes it before returning valid credentials.

    Args:
        user_id: The ID of the user
        db_service: Database service (optional, uses singleton if not provided)

    Returns:
        Credentials: Valid Google OAuth2 credentials object

    Raises:
        ValueError: If user not found or tokens missing
        Exception: If token refresh or retrieval fails
    """
    # Use provided service or fall back to singleton
    if db_service is None:
        db_service = database_service

    try:
        user = await db_service.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.gmail_oauth_token or not user.gmail_refresh_token:
            raise ValueError(f"Gmail tokens not configured for user {user_id}")

        # Decrypt tokens
        access_token = decrypt_token(user.gmail_oauth_token)
        refresh_token = decrypt_token(user.gmail_refresh_token)

        # Create credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
        )

        # Check if token needs refresh (expired or about to expire)
        if credentials.expired:
            logger.info("token_expired_refreshing", user_id=user_id)
            await refresh_access_token(user_id, db_service)

            # Reload user to get updated token
            user = await db_service.get_user(user_id)
            access_token = decrypt_token(user.gmail_oauth_token)
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GMAIL_CLIENT_ID,
                client_secret=settings.GMAIL_CLIENT_SECRET,
            )

        return credentials

    except ValueError:
        raise
    except Exception as e:
        logger.error("get_gmail_credentials_failed", user_id=user_id, error=str(e), exc_info=True)
        raise Exception(f"Failed to get Gmail credentials: {str(e)}")
