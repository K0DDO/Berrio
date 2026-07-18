from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_BACKEND_DIR / ".env.local"),
            str(_BACKEND_DIR / ".env"),
            ".env.local",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Berrio"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    secret_key: str = Field(default="dev-only-change-me-use-long-random-string")
    field_encryption_key: str | None = None
    email_hash_pepper: str = Field(default="berrio-email-pepper-change-me")
    require_secure_secrets: bool = False

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    email_verification_enabled: bool = False
    password_reset_enabled: bool = False
    email_verification_expire_hours: int = 24
    password_reset_expire_hours: int = 1

    kimi_api_key: str | None = None
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"

    fns_provider: str = "auto"
    fns_api_token: str | None = None
    fns_api_url: str = "https://proverkacheka.com/api/v1/check/get"

    database_url: str = "postgresql+asyncpg://berrio:berrio@localhost:5432/berrio"
    database_url_sync: str = "postgresql://berrio:berrio@localhost:5432/berrio"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    api_rate_limit_per_minute: int = 180
    seed_demo_data: bool = False

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "*",
        ]
    )

    @field_validator("app_env")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def _reject_blank_required(self) -> Settings:
        blanks: list[str] = []
        if not (self.secret_key or "").strip():
            blanks.append("SECRET_KEY")
        if not (self.database_url or "").strip():
            blanks.append("DATABASE_URL")
        if not (self.email_hash_pepper or "").strip():
            blanks.append("EMAIL_HASH_PEPPER")
        if blanks:
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(blanks)
                + ". Copy backend/.env.local.example → backend/.env.local and fill them in. "
                "See docs/local-development.md."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
