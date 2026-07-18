"""JWT signing key length / production safety."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_jwt_signing_key_falls_back_to_secret_key() -> None:
    s = Settings(
        secret_key="x" * 32,
        jwt_secret=None,
        email_hash_pepper="pepper-ok",
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_env="development",
    )
    assert s.jwt_signing_key == "x" * 32


def test_jwt_secret_preferred_over_secret_key() -> None:
    s = Settings(
        secret_key="s" * 32,
        jwt_secret="j" * 40,
        email_hash_pepper="pepper-ok",
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_env="development",
    )
    assert s.jwt_signing_key == "j" * 40


def test_production_rejects_short_jwt_key() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(
            secret_key="short",
            jwt_secret=None,
            email_hash_pepper="not-the-dev-pepper-value",
            database_url="postgresql+asyncpg://u:p@localhost/db",
            app_env="production",
            require_secure_secrets=True,
        )
    assert "32 bytes" in str(exc.value)
