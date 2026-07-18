"""Production security middleware helpers."""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

_IP_HITS: dict[str, list[float]] = defaultdict(list)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline browser / API hardening headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), microphone=(), geolocation=()",
        )
        response.headers.setdefault("X-XSS-Protection", "0")
        settings = get_settings()
        if not settings.debug:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP sliding window (in-process). Prefer edge limits in multi-instance."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        limit = settings.api_rate_limit_per_minute
        if limit <= 0 or request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = [t for t in _IP_HITS[client] if now - t < 60]
        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": "60"},
            )
        window.append(now)
        _IP_HITS[client] = window
        return await call_next(request)


def resolve_cors_origins() -> list[str]:
    """Never allow wildcard CORS outside debug."""
    settings = get_settings()
    origins = list(settings.cors_origins)
    if settings.debug:
        return origins
    return [o for o in origins if o != "*"]


def warn_insecure_defaults() -> list[str]:
    """Return warnings for known insecure default settings (startup / review)."""
    settings = get_settings()
    issues: list[str] = []
    if (
        not settings.secret_key
        or settings.secret_key.startswith("dev-only")
        or settings.secret_key == "change-me-in-production-use-long-random-string"
    ):
        issues.append("SECRET_KEY is still the development default")
    if not settings.email_hash_pepper or settings.email_hash_pepper.startswith(
        "berrio-email-pepper"
    ):
        issues.append("EMAIL_HASH_PEPPER is still the development default")
    if not settings.field_encryption_key and settings.app_env == "production":
        issues.append("FIELD_ENCRYPTION_KEY is unset in production")
    if not settings.debug and "*" in settings.cors_origins:
        issues.append("CORS wildcard is configured while debug=False")
    if settings.app_env == "production" and settings.debug:
        issues.append("DEBUG is enabled in production environment")
    return issues


def assert_secure_startup() -> None:
    """Raise if production demands secure secrets and defaults remain."""
    settings = get_settings()
    if not (settings.require_secure_secrets or settings.app_env == "production"):
        return
    blockers = [
        i
        for i in warn_insecure_defaults()
        if "SECRET_KEY" in i or "EMAIL_HASH_PEPPER" in i or "DEBUG is enabled" in i
    ]
    if blockers:
        raise RuntimeError(
            "Insecure production configuration: "
            + "; ".join(blockers)
            + ". Set real secrets in backend/.env.prod (see .env.prod.example)."
        )


def validate_required_env() -> None:
    """Human-readable check after settings load (complements pydantic validator)."""
    settings = get_settings()
    problems: list[str] = []
    if not settings.secret_key.strip():
        problems.append("SECRET_KEY is empty")
    if not settings.database_url.strip():
        problems.append("DATABASE_URL is empty")
    if "CHANGE_ME" in settings.database_url.upper():
        problems.append("DATABASE_URL still contains CHANGE_ME placeholder")
    if problems:
        raise RuntimeError(
            "Berrio cannot start — fix environment:\n  - "
            + "\n  - ".join(problems)
            + "\nCopy backend/.env.local.example → backend/.env.local "
            "(see docs/local-development.md)."
        )
