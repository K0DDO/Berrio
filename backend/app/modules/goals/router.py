from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.families.permission_checker import (
    FamilyPermissionChecker,
    FamilyPermissionKey,
)
from app.modules.goals.schemas import (
    GoalCreate,
    GoalOut,
    GoalProgressUpdate,
    GoalUpdate,
)
from app.modules.goals.service import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalOut, status_code=201)
async def create_goal(
    body: GoalCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoalOut:
    checker = FamilyPermissionChecker(session)
    if body.family_id is not None:
        await checker.assert_can(
            actor_id=user_id,
            family_id=body.family_id,
            permission=FamilyPermissionKey.GOALS,
        )
    service = GoalService(session)
    result = await service.create(user_id, body)
    await session.commit()
    return result


@router.get("", response_model=list[GoalOut])
async def list_goals(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> list[GoalOut]:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.GOALS,
    )
    service = GoalService(session)
    return await service.list_for_users(scope)


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal(
    goal_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> GoalOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.GOALS,
    )
    return await GoalService(session).get(scope, goal_id)


@router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: UUID,
    body: GoalUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> GoalOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.GOALS,
    )
    result = await GoalService(session).update(scope, user_id, goal_id, body)
    await session.commit()
    return result


@router.post("/{goal_id}/progress", response_model=GoalOut)
async def update_goal_progress(
    goal_id: UUID,
    body: GoalProgressUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> GoalOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.GOALS,
    )
    result = await GoalService(session).update_progress(scope, user_id, goal_id, body)
    await session.commit()
    return result


@router.post("/{goal_id}/archive", response_model=GoalOut)
async def archive_goal(
    goal_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> GoalOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.GOALS,
    )
    result = await GoalService(session).archive(scope, user_id, goal_id)
    await session.commit()
    return result
