"""Production security middleware helpers."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings


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
    if settings.secret_key.startswith("dev-only"):
        issues.append("SECRET_KEY is still the development default")
    if settings.email_hash_pepper.startswith("berrio-email-pepper"):
        issues.append("EMAIL_HASH_PEPPER is still the development default")
    if not settings.debug and "*" in settings.cors_origins:
        issues.append("CORS wildcard is configured while debug=False")
    if settings.app_env == "production" and settings.debug:
        issues.append("DEBUG is enabled in production environment")
    return issues
