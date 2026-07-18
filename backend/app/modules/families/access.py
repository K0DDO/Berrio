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
        """
        CHILD → only self.
        PARENT/OWNER with can_view_children → self + children.
        Otherwise → self.
        """
        member = await self.member_of(actor_id, family_id)
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a family member")

        if member.role == FamilyRole.CHILD:
            return [actor_id]

        can_view = False
        result = await self._session.execute(
            select(FamilyPermission).where(
                FamilyPermission.member_id == member.id,
                FamilyPermission.permission_key == "can_view_children",
            )
        )
        perm = result.scalar_one_or_none()
        can_view = bool(perm and perm.allowed) or member.role == FamilyRole.OWNER

        if not can_view:
            return [actor_id]

        members = await self._session.execute(
            select(FamilyMember).where(FamilyMember.family_id == family_id)
        )
        ids = [actor_id]
        for m in members.scalars().all():
            if m.role == FamilyRole.CHILD and m.user_id not in ids:
                ids.append(m.user_id)
        return ids
