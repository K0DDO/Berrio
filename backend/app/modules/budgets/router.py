from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.budgets.schemas import BudgetCreate, BudgetOut, BudgetUpdate
from app.modules.budgets.service import BudgetService
from app.modules.families.permission_checker import FamilyPermissionChecker, FamilyPermissionKey

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetOut, status_code=201)
async def create_budget(
    body: BudgetCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BudgetOut:
    checker = FamilyPermissionChecker(session)
    if body.family_id is not None:
        await checker.assert_can(
            actor_id=user_id,
            family_id=body.family_id,
            permission=FamilyPermissionKey.BUDGETS,
        )
    result = await BudgetService(session).create(user_id, body)
    await session.commit()
    return result


@router.get("", response_model=list[BudgetOut])
async def list_budgets(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> list[BudgetOut]:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.BUDGETS,
    )
    return await BudgetService(session).list_for_users(scope)


@router.get("/{budget_id}", response_model=BudgetOut)
async def get_budget(
    budget_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> BudgetOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.BUDGETS,
    )
    return await BudgetService(session).get(scope, budget_id)


@router.patch("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: UUID,
    body: BudgetUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> BudgetOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.BUDGETS,
    )
    result = await BudgetService(session).update(scope, user_id, budget_id, body)
    await session.commit()
    return result


@router.post("/{budget_id}/check", response_model=BudgetOut)
async def check_budget(
    budget_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> BudgetOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.BUDGETS,
    )
    result = await BudgetService(session).check_thresholds(scope, budget_id)
    await session.commit()
    return result


@router.post("/{budget_id}/archive", response_model=BudgetOut)
async def archive_budget(
    budget_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> BudgetOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.BUDGETS,
    )
    result = await BudgetService(session).archive(scope, user_id, budget_id)
    await session.commit()
    return result
