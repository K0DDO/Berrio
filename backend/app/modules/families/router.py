from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.families.service import (
    FamilyCreate,
    FamilyOut,
    FamilyService,
    MemberOut,
    PermissionUpdate,
)

router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=FamilyOut, status_code=201)
async def create_family(
    body: FamilyCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FamilyOut:
    service = FamilyService(session)
    family = await service.create_family(user_id, body)
    await session.commit()
    return FamilyOut.model_validate(family)


@router.get("", response_model=list[FamilyOut])
async def list_families(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[FamilyOut]:
    service = FamilyService(session)
    rows = await service.list_families(user_id)
    return [FamilyOut.model_validate(r) for r in rows]


@router.get("/{family_id}/members", response_model=list[MemberOut])
async def list_members(
    family_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[MemberOut]:
    service = FamilyService(session)
    return await service.get_members(user_id, family_id)


@router.get("/{family_id}/visible-user-ids", response_model=list[UUID])
async def visible_user_ids(
    family_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[UUID]:
    """Data isolation helper: which user IDs the actor may see in this family."""
    from app.modules.families.access import FamilyAccessService

    access = FamilyAccessService(session)
    return await access.visible_user_ids(user_id, family_id)


@router.patch("/{family_id}/members/{member_id}/permissions", response_model=MemberOut)
async def patch_permission(
    family_id: UUID,
    member_id: UUID,
    body: PermissionUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MemberOut:
    service = FamilyService(session)
    result = await service.update_permission(user_id, family_id, member_id, body)
    await session.commit()
    return result
