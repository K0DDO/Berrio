"""Password hashing, JWT, refresh-token hashing, email lookup hash."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import Type

from app.core.config import get_settings
from app.core.encryption import get_encryption_service

# Argon2id — OWASP-aligned defaults for interactive logins
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except Exception:
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_email(email: str) -> str:
    """
    Lookup key: normalize → SHA-256(pepper || email).

    Pepper prevents offline rainbow-table attacks on stolen email_hash columns.
    Raw email is never stored in email_hash.
    """
    settings = get_settings()
    normalized = normalize_email(email).encode("utf-8")
    pepper = settings.email_hash_pepper.encode("utf-8")
    return hashlib.sha256(pepper + normalized).hexdigest()


def encrypt_email(email: str) -> bytes:
    """Encrypt normalized email with AES-256-GCM."""
    return get_encryption_service().encrypt_str(normalize_email(email))


def decrypt_email(email_enc: bytes) -> str:
    return get_encryption_service().decrypt_str(email_enc)


def hash_token(raw_token: str) -> str:
    """Store only hashes of refresh / verification / reset tokens."""
    settings = get_settings()
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(*, user_id: UUID, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "type"]},
    )
