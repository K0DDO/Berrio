from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security_middleware import (
    ApiRateLimitMiddleware,
    SecurityHeadersMiddleware,
    assert_secure_startup,
    resolve_cors_origins,
    validate_required_env,
    warn_insecure_defaults,
)

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging(debug=settings.debug, level=settings.log_level)
    validate_required_env()
    assert_secure_startup()
    for warning in warn_insecure_defaults():
        logger.warning("berrio.security_warning", detail=warning)
    logger.info("berrio.startup", env=settings.app_env, version="0.1.0")
    if settings.seed_demo_data:
        from app.modules.dev.seed import maybe_seed_on_startup

        await maybe_seed_on_startup()
    yield
    logger.info("berrio.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ApiRateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolve_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
