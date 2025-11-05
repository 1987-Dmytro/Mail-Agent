"""Tests for OAuth token encryption utilities."""

import pytest

from app.core.encryption import (
    decrypt_token,
    encrypt_token,
)


def test_encrypt_decrypt_roundtrip():
    """Test that encryption and decryption roundtrip works correctly."""
    original_token = "ya29.a0AfB_byDexample1234567890"

    # Encrypt the token
    encrypted = encrypt_token(original_token)

    # Verify it's different from original
    assert encrypted != original_token
    assert len(encrypted) > len(original_token)  # Base64 encoded

    # Decrypt the token
    decrypted = decrypt_token(encrypted)

    # Verify roundtrip
    assert decrypted == original_token


def test_encrypt_different_tokens_produce_different_ciphertexts():
    """Test that different tokens produce different encrypted outputs."""
    token1 = "ya29.a0AfB_byDtoken1"
    token2 = "ya29.a0AfB_byDtoken2"

    encrypted1 = encrypt_token(token1)
    encrypted2 = encrypt_token(token2)

    assert encrypted1 != encrypted2


def test_decrypt_invalid_ciphertext_raises_exception():
    """Test that decrypting invalid ciphertext raises an exception."""
    invalid_ciphertext = "this-is-not-a-valid-encrypted-token"

    with pytest.raises(Exception) as exc_info:
        decrypt_token(invalid_ciphertext)

    assert "Failed to decrypt token" in str(exc_info.value)


def test_encrypt_empty_string():
    """Test encrypting an empty string."""
    empty_token = ""

    encrypted = encrypt_token(empty_token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == empty_token


def test_encrypt_long_token():
    """Test encrypting a very long token."""
    long_token = "ya29.a0AfB_byD" + ("x" * 1000)

    encrypted = encrypt_token(long_token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == long_token


def test_encrypt_token_with_special_characters():
    """Test encrypting tokens with special characters."""
    special_token = "ya29.a0AfB_byD!@#$%^&*()_+-=[]{}|;:',.<>?/~`"

    encrypted = encrypt_token(special_token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == special_token
