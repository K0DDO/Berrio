from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.modules.events import get_event_bus
from app.modules.events.base import DomainEvent

router = APIRouter()


@router.get("/system/modules")
async def list_foundation_modules() -> dict[str, list[str]]:
    """Foundation shelf map — confirms modular layout is wired."""
    return {
        "modules": [
            "auth",
            "users",
            "families",
            "categories",
            "categorization",
            "receipts",
            "products",
            "merchants",
            "transactions",
            "banks",
            "budgets",
            "goals",
            "analytics",
            "financial_health",
            "notifications",
            "ai",
            "audit",
            "events",
        ]
    }


@router.post("/system/events/ping")
async def ping_event_bus() -> dict[str, str]:
    """Smoke-test EventBus abstraction (log-only in Sprint 1)."""
    bus = get_event_bus()
    await bus.publish(DomainEvent(event_type="system.ping", payload={"source": "api"}))
    return {"status": "published", "event_type": "system.ping"}


@router.post("/system/seed-demo")
async def seed_demo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Load demo user + receipts (development only)."""
    settings = get_settings()
    if settings.app_env == "production" or not settings.debug:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Demo seed is disabled outside development",
        )
    from app.modules.dev.seed import seed_demo_data

    return await seed_demo_data(session)
