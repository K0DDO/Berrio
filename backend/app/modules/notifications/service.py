"""
NotificationService — persist explainable alerts and fan-out to channels.

Pipeline:
  Domain Event / domain signal
        ↓
  Notification Rules Engine
        ↓
  Preferences + dedupe gate
        ↓
  Notification (persisted)
        ↓
  Channels (InApp MVP; Push/Email interfaces ready)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.channels import InAppChannel, NotificationChannel
from app.modules.notifications.models import Notification, NotificationType
from app.modules.notifications.preferences import NotificationPreferences
from app.modules.notifications.rules import NotificationRulesEngine
from app.modules.notifications.schemas import NotificationCreate, NotificationOut


_PREF_MAP = {
    NotificationType.PRICE_CHANGE: "price_changes_enabled",
    NotificationType.BUDGET_WARNING: "budget_alerts_enabled",
    NotificationType.BUDGET_EXCEEDED: "budget_alerts_enabled",
    NotificationType.GOAL_PROGRESS: "goal_alerts_enabled",
    NotificationType.AI_INSIGHT: "ai_insights_enabled",
    NotificationType.UNUSUAL_SPENDING: "unusual_spending_enabled",
}


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        channels: list[NotificationChannel] | None = None,
        rules: NotificationRulesEngine | None = None,
    ) -> None:
        self._session = session
        self._rules = rules or NotificationRulesEngine()
        self._channels: list[NotificationChannel] = list(channels) if channels else [InAppChannel()]

    @property
    def rules(self) -> NotificationRulesEngine:
        return self._rules

    def register_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)

    async def create_and_dispatch(self, draft: NotificationCreate) -> NotificationOut | None:
        if not await self._pref_allows(draft.user_id, draft.type):
            return None

        if draft.dedupe_key:
            existing = await self._session.execute(
                select(Notification).where(
                    Notification.user_id == draft.user_id,
                    Notification.dedupe_key == draft.dedupe_key,
                )
            )
            found = existing.scalar_one_or_none()
            if found is not None:
                return NotificationOut.model_validate(found)

        row = Notification(
            user_id=draft.user_id,
            family_id=draft.family_id,
            type=draft.type.value,
            title=draft.title,
            message=draft.message,
            severity=draft.severity.value,
            payload=draft.payload,
            dedupe_key=draft.dedupe_key,
        )
        self._session.add(row)
        await self._session.flush()
        for channel in self._channels:
            await channel.send(row)
        return NotificationOut.model_validate(row)

    async def dispatch_many(self, drafts: list[NotificationCreate]) -> list[NotificationOut]:
        out: list[NotificationOut] = []
        for d in drafts:
            created = await self.create_and_dispatch(d)
            if created is not None:
                out.append(created)
        return out

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[NotificationOut]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        result = await self._session.execute(stmt)
        return [NotificationOut.model_validate(r) for r in result.scalars().all()]

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> NotificationOut:
        result = await self._session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found")
        if row.read_at is None:
            row.read_at = datetime.now(UTC)
            await self._session.flush()
        return NotificationOut.model_validate(row)

    async def notify(
        self,
        *,
        user_id: UUID,
        type,
        title: str,
        message: str,
        family_id: UUID | None = None,
        severity=None,
        payload: dict | None = None,
        dedupe_key: str | None = None,
    ) -> NotificationOut | None:
        from app.modules.notifications.models import NotificationSeverity

        ntype = type if isinstance(type, NotificationType) else NotificationType(str(type))
        sev = severity or NotificationSeverity.INFO
        if isinstance(sev, str):
            sev = NotificationSeverity(sev)
        return await self.create_and_dispatch(
            NotificationCreate(
                user_id=user_id,
                family_id=family_id,
                type=ntype,
                title=title,
                message=message,
                severity=sev,
                payload=payload or {},
                dedupe_key=dedupe_key,
            )
        )

    async def _pref_allows(self, user_id: UUID, ntype: NotificationType) -> bool:
        attr = _PREF_MAP.get(ntype)
        if attr is None:
            return True
        result = await self._session.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            return True
        return bool(getattr(prefs, attr, True))
