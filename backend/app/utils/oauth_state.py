"""OAuth state management using Redis.

This module provides utilities for storing and validating OAuth state tokens
in Redis to prevent CSRF attacks in the OAuth flow.
"""

import redis
from app.core.config import settings
from app.core.logging import logger

# Initialize Redis client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,  # Automatically decode bytes to strings
)

# OAuth state TTL: 10 minutes (enough for user to complete OAuth flow)
OAUTH_STATE_TTL = 600


def store_oauth_state(state: str) -> bool:
    """Store OAuth state token in Redis with TTL.

    Args:
        state: The OAuth state token to store

    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        # Store state with 10-minute expiration
        redis_client.setex(
            name=f"oauth_state:{state}",
            time=OAUTH_STATE_TTL,
            value="1",  # Value doesn't matter, we just check existence
        )
        logger.info("oauth_state_stored", state_prefix=state[:10] + "...")
        return True
    except Exception as e:
        logger.error("oauth_state_store_failed", error=str(e), exc_info=True)
        return False


def validate_oauth_state(state: str) -> bool:
    """Validate OAuth state token from Redis.

    Checks if the state exists in Redis and deletes it if found (one-time use).

    Args:
        state: The OAuth state token to validate

    Returns:
        bool: True if state is valid and found, False otherwise
    """
    try:
        key = f"oauth_state:{state}"

        # Check if state exists
        exists = redis_client.exists(key)

        if exists:
            # Delete state (one-time use)
            redis_client.delete(key)
            logger.info("oauth_state_validated", state_prefix=state[:10] + "...")
            return True
        else:
            logger.warning("oauth_state_not_found", state_prefix=state[:10] + "...")
            return False
    except Exception as e:
        logger.error("oauth_state_validation_failed", error=str(e), exc_info=True)
        return False


def cleanup_expired_states() -> int:
    """Cleanup expired OAuth states (for debugging/maintenance).

    Redis automatically removes expired keys, but this function can be used
    to manually cleanup if needed.

    Returns:
        int: Number of states cleaned up
    """
    try:
        # Get all oauth_state keys
        keys = redis_client.keys("oauth_state:*")

        # Count expired keys (TTL = -2 means key doesn't exist, -1 means no expiry)
        expired_count = 0
        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl == -2:  # Key doesn't exist (expired)
                expired_count += 1

        logger.info("oauth_states_cleanup", expired_count=expired_count, total_keys=len(keys))
        return expired_count
    except Exception as e:
        logger.error("oauth_states_cleanup_failed", error=str(e), exc_info=True)
        return 0
