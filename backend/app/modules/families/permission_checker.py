"""
Unified family permission checker for all family-scoped domains.

Usage in routers:
  checker = FamilyPermissionChecker(session)
  user_ids = await checker.resolve_scope(
      actor_id=user_id,
      family_id=family_id,  # optional query param
      permission=FamilyPermissionKey.CAN_VIEW_FAMILY_BUDGET,
  )
  # then filter domain queries by user_ids
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.families.models import FamilyMember, FamilyPermission, FamilyRole


class FamilyPermissionKey(StrEnum):
    CAN_VIEW_FAMILY_BUDGET = "can_view_family_budget"
    CAN_VIEW_CHILDREN = "can_view_children"
    CAN_MANAGE_GOALS = "can_manage_goals"
    CAN_RECEIVE_REPORTS = "can_receive_reports"
    CAN_INVITE_MEMBERS = "can_invite_members"
    # Domain aliases used by API layers
    RECEIPTS = "can_view_family_budget"
    ANALYTICS = "can_view_family_budget"
    TRANSACTIONS = "can_view_family_budget"
    AI_INSIGHTS = "can_receive_reports"


class FamilyPermissionChecker:
    """Single entry-point for family RBAC across receipts/analytics/banks/AI."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_scope(
        self,
        *,
        actor_id: UUID,
        family_id: UUID | None,
        permission: FamilyPermissionKey | str,
    ) -> list[UUID]:
        """
        Returns user_ids the actor may read for this domain.

        - No family_id → only actor (personal scope).
        - With family_id → enforce membership + permission, then visible users.
        """
        if family_id is None:
            return [actor_id]

        key = permission.value if isinstance(permission, FamilyPermissionKey) else permission
        member = await self._require_member(actor_id, family_id)
        await self._require_permission(member, key)
        return await self._visible_user_ids(member, family_id)

    async def assert_can(
        self,
        *,
        actor_id: UUID,
        family_id: UUID,
        permission: FamilyPermissionKey | str,
    ) -> FamilyMember:
        key = permission.value if isinstance(permission, FamilyPermissionKey) else permission
        member = await self._require_member(actor_id, family_id)
        await self._require_permission(member, key)
        return member

    async def _require_member(self, user_id: UUID, family_id: UUID) -> FamilyMember:
        result = await self._session.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a family member")
        return member

    async def _require_permission(self, member: FamilyMember, permission_key: str) -> None:
        if member.role == FamilyRole.OWNER:
            return
        result = await self._session.execute(
            select(FamilyPermission).where(
                FamilyPermission.member_id == member.id,
                FamilyPermission.permission_key == permission_key,
            )
        )
        perm = result.scalar_one_or_none()
        if perm is None or not perm.allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_key}",
            )

    async def _visible_user_ids(self, member: FamilyMember, family_id: UUID) -> list[UUID]:
        if member.role == FamilyRole.CHILD:
            return [member.user_id]

        # Parents/owners: self + children if can_view_children (owners always)
        can_view_children = member.role == FamilyRole.OWNER
        if not can_view_children:
            result = await self._session.execute(
                select(FamilyPermission).where(
                    FamilyPermission.member_id == member.id,
                    FamilyPermission.permission_key == FamilyPermissionKey.CAN_VIEW_CHILDREN,
                )
            )
            perm = result.scalar_one_or_none()
            can_view_children = bool(perm and perm.allowed)

        ids = [member.user_id]
        if not can_view_children:
            return ids

        members = await self._session.execute(
            select(FamilyMember).where(FamilyMember.family_id == family_id)
        )
        for m in members.scalars().all():
            if m.role == FamilyRole.CHILD and m.user_id not in ids:
                ids.append(m.user_id)
        return ids
