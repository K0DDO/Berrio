"""Family access helpers — enforce permissions across domains."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.families.models import FamilyMember, FamilyPermission, FamilyRole


class FamilyAccessService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def member_of(self, user_id: UUID, family_id: UUID) -> FamilyMember | None:
        result = await self._session.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def require_permission(
        self, user_id: UUID, family_id: UUID, permission_key: str
    ) -> FamilyMember:
        member = await self.member_of(user_id, family_id)
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a family member")
        result = await self._session.execute(
            select(FamilyPermission).where(
                FamilyPermission.member_id == member.id,
                FamilyPermission.permission_key == permission_key,
            )
        )
        perm = result.scalar_one_or_none()
        allowed = perm.allowed if perm is not None else False
        if not allowed and member.role != FamilyRole.OWNER:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission_key}")
        return member

    async def visible_user_ids(self, actor_id: UUID, family_id: UUID) -> list[UUID]:
        """Deprecated wrapper — use FamilyPermissionChecker.resolve_scope."""
        from app.modules.families.permission_checker import (
            FamilyPermissionChecker,
            FamilyPermissionKey,
        )

        checker = FamilyPermissionChecker(self._session)
        return await checker.resolve_scope(
            actor_id=actor_id,
            family_id=family_id,
            permission=FamilyPermissionKey.CAN_VIEW_CHILDREN,
        )
