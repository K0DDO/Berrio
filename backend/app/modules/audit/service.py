from datetime import UTC, datetime
from typing import Any
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AuditLog


class AuditService:
    """Append-only audit writer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        action: str,
        actor_user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        family_id: UUID | None = None,
        ip_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            family_id=family_id,
            ip_hash=ip_hash,
            metadata_json=json.dumps(metadata or {}, default=str),
            created_at=datetime.now(UTC),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
