"""Token encryption utilities for secure storage of OAuth tokens.

This module provides functions for encrypting and decrypting OAuth tokens
using Fernet symmetric encryption (AES-128-CBC with HMAC authentication).
"""

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logging import logger


def encrypt_token(plaintext: str) -> str:
    """Encrypt OAuth token using Fernet symmetric encryption.

    Args:
        plaintext: The token to encrypt (access_token or refresh_token)

    Returns:
        str: Base64-encoded encrypted token

    Raises:
        ValueError: If encryption key is not configured
        Exception: If encryption fails
    """
    try:
        if not settings.ENCRYPTION_KEY:
            logger.error("encryption_key_missing")
            raise ValueError("ENCRYPTION_KEY environment variable not configured")

        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        encrypted = cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error("token_encryption_failed", error=str(e), exc_info=True)
        raise Exception(f"Failed to encrypt token: {str(e)}")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt OAuth token.

    Args:
        ciphertext: The encrypted token (base64-encoded)

    Returns:
        str: Decrypted plaintext token

    Raises:
        ValueError: If encryption key is not configured
        Exception: If decryption fails (invalid key, corrupted data, expired token)
    """
    try:
        if not settings.ENCRYPTION_KEY:
            logger.error("encryption_key_missing")
            raise ValueError("ENCRYPTION_KEY environment variable not configured")

        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted = cipher.decrypt(ciphertext.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error("token_decryption_failed", error=str(e), exc_info=True)
        raise Exception(f"Failed to decrypt token: {str(e)}")
