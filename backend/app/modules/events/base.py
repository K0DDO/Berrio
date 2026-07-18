from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base contract for all Berrio domain events."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_user_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID | None = None
