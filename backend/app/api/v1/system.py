from fastapi import APIRouter

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
    await bus.publish(
        DomainEvent(event_type="system.ping", payload={"source": "api"})
    )
    return {"status": "published", "event_type": "system.ping"}
