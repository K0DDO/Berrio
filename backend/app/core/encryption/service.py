"""Field-level encryption — AES-256-GCM."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

# Wire format: version(1) || nonce(12) || ciphertext+tag
_VERSION = b"\x01"
_NONCE_LEN = 12


class EncryptionError(Exception):
    """Raised when ciphertext cannot be decrypted."""


class EncryptionService:
    """
    AES-256-GCM encrypt/decrypt for sensitive fields (email, etc.).

    Key is derived via SHA-256 from FIELD_ENCRYPTION_KEY or SECRET_KEY.
    Output: version || nonce || ciphertext (includes GCM auth tag).
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key")
        self._aesgcm = AESGCM(key)

    @classmethod
    def from_settings(cls) -> EncryptionService:
        settings = get_settings()
        material = (settings.field_encryption_key or settings.secret_key).encode("utf-8")
        key = hashlib.sha256(material).digest()
        return cls(key)

    def encrypt(self, plaintext: str | bytes, *, associated_data: bytes | None = None) -> bytes:
        data = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
        nonce = os.urandom(_NONCE_LEN)
        ciphertext = self._aesgcm.encrypt(nonce, data, associated_data)
        return _VERSION + nonce + ciphertext

    def decrypt(self, blob: bytes, *, associated_data: bytes | None = None) -> bytes:
        if len(blob) < 1 + _NONCE_LEN + 16:
            raise EncryptionError("Ciphertext too short")
        if blob[0:1] != _VERSION:
            raise EncryptionError("Unsupported ciphertext version")
        nonce = blob[1 : 1 + _NONCE_LEN]
        ciphertext = blob[1 + _NONCE_LEN :]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, associated_data)
        except Exception as exc:  # InvalidTag, etc.
            raise EncryptionError("Decryption failed") from exc

    def encrypt_str(self, plaintext: str, *, associated_data: bytes | None = None) -> bytes:
        return self.encrypt(plaintext, associated_data=associated_data)

    def decrypt_str(self, blob: bytes, *, associated_data: bytes | None = None) -> str:
        return self.decrypt(blob, associated_data=associated_data).decode("utf-8")


@lru_cache
def get_encryption_service() -> EncryptionService:
    return EncryptionService.from_settings()
