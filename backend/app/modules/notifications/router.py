from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.notifications.preferences import NotificationPreferences
from app.modules.notifications.preferences_schemas import (
    NotificationPreferencesOut,
    NotificationPreferencesUpdate,
)
from app.modules.notifications.schemas import NotificationOut
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _get_or_create_prefs(session: AsyncSession, user_id: UUID) -> NotificationPreferences:
    result = await session.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = NotificationPreferences(user_id=user_id)
        session.add(row)
        await session.flush()
    return row


@router.get("/preferences", response_model=NotificationPreferencesOut)
async def get_preferences(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferencesOut:
    row = await _get_or_create_prefs(session, user_id)
    await session.commit()
    return NotificationPreferencesOut.model_validate(row)


@router.patch("/preferences", response_model=NotificationPreferencesOut)
async def update_preferences(
    body: NotificationPreferencesUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferencesOut:
    row = await _get_or_create_prefs(session, user_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return NotificationPreferencesOut.model_validate(row)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NotificationOut]:
    return await NotificationService(session).list_for_user(
        user_id, unread_only=unread_only, limit=limit
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationOut:
    result = await NotificationService(session).mark_read(user_id, notification_id)
    await session.commit()
    return result
