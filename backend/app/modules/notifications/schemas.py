from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.notifications.models import NotificationSeverity, NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    family_id: UUID | None
    type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity
    payload: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str | None = None
    created_at: datetime
    read_at: datetime | None


class NotificationCreate(BaseModel):
    """Internal draft produced by the rules engine."""

    user_id: UUID
    family_id: UUID | None = None
    type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    payload: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str | None = None
