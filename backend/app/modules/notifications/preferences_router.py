from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.notifications.preferences import NotificationPreferences
from app.modules.notifications.preferences_schemas import (
    NotificationPreferencesOut,
    NotificationPreferencesUpdate,
)

prefs_router = APIRouter(prefix="/notifications/preferences", tags=["notifications"])


async def _get_or_create(session: AsyncSession, user_id: UUID) -> NotificationPreferences:
    result = await session.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = NotificationPreferences(user_id=user_id)
        session.add(row)
        await session.flush()
    return row


@prefs_router.get("", response_model=NotificationPreferencesOut)
async def get_preferences(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferencesOut:
    row = await _get_or_create(session, user_id)
    await session.commit()
    return NotificationPreferencesOut.model_validate(row)


@prefs_router.patch("", response_model=NotificationPreferencesOut)
async def update_preferences(
    body: NotificationPreferencesUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferencesOut:
    row = await _get_or_create(session, user_id)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return NotificationPreferencesOut.model_validate(row)
