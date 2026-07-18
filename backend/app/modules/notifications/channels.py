"""Delivery channels — InApp is MVP; Push/Email are prepared interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from app.modules.notifications.models import Notification, NotificationType


@runtime_checkable
class NotificationChannel(Protocol):
    async def send(self, notification: Notification) -> None:
        """Deliver a persisted notification to the channel."""


@runtime_checkable
class PushChannel(Protocol):
    """Push delivery interface — implement with FCM/APNs later."""

    async def send_push(
        self,
        *,
        user_id: UUID,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None: ...


@runtime_checkable
class EmailChannel(Protocol):
    """Email delivery interface — implement with SMTP/ESP later."""

    async def send_email(
        self,
        *,
        user_id: UUID,
        subject: str,
        body: str,
    ) -> None: ...


class InAppChannel:
    """
    MVP channel: notification is already persisted in DB and exposed via API.
    This class exists so the pipeline always has at least one registered channel.
    """

    async def send(self, notification: Notification) -> None:
        return None


class StubPushChannel:
    """Prepared PushChannel — no delivery yet."""

    async def send_push(
        self,
        *,
        user_id: UUID,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        raise NotImplementedError("PushChannel is not configured")


class StubEmailChannel:
    """Prepared EmailChannel — no delivery yet."""

    async def send_email(
        self,
        *,
        user_id: UUID,
        subject: str,
        body: str,
    ) -> None:
        raise NotImplementedError("EmailChannel is not configured")


# Re-export type for older call sites
__all__ = [
    "EmailChannel",
    "InAppChannel",
    "NotificationChannel",
    "NotificationType",
    "PushChannel",
    "StubEmailChannel",
    "StubPushChannel",
]
