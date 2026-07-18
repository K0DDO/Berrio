from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    # Fail fast in production if secrets look like defaults
    require_secure_secrets: bool = False

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Architectural prep — email sending not wired yet
    email_verification_enabled: bool = False
    password_reset_enabled: bool = False
    email_verification_expire_hours: int = 24
    password_reset_expire_hours: int = 1

    kimi_api_key: str | None = None
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"

    # FNS / OFD receipt provider (proverkacheka.com partner API)
    fns_provider: str = "auto"  # auto | stub | proverkacheka
    fns_api_token: str | None = None
    fns_api_url: str = "https://proverkacheka.com/api/v1/check/get"

    database_url: str = "postgresql+asyncpg://berrio:berrio@localhost:5432/berrio"
    database_url_sync: str = "postgresql://berrio:berrio@localhost:5432/berrio"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Soft API rate limit (per client IP, in-process)
    api_rate_limit_per_minute: int = 180

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
