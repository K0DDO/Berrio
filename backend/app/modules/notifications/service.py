"""
Notifications — in-app, push, email channels.

Types: PRICE_CHANGE, BUDGET_WARNING, AI_INSIGHT, GOAL_PROGRESS, SYSTEM.
"""

from enum import StrEnum
from typing import Protocol
from uuid import UUID


class NotificationType(StrEnum):
    PRICE_CHANGE = "PRICE_CHANGE"
    BUDGET_WARNING = "BUDGET_WARNING"
    AI_INSIGHT = "AI_INSIGHT"
    GOAL_PROGRESS = "GOAL_PROGRESS"
    SYSTEM = "SYSTEM"


class NotificationChannel(Protocol):
    async def send(
        self,
        *,
        user_id: UUID,
        type: NotificationType,
        title: str,
        message: str,
    ) -> None: ...


class NotificationService:
    """Fan-out stub — channels registered in later stages."""

    def __init__(self) -> None:
        self._channels: list[NotificationChannel] = []

    def register_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)

    async def notify(
        self,
        *,
        user_id: UUID,
        type: NotificationType,
        title: str,
        message: str,
    ) -> None:
        for channel in self._channels:
            await channel.send(user_id=user_id, type=type, title=title, message=message)
