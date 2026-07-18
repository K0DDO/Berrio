from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.families.models import (
    DEFAULT_PERMISSIONS,
    Family,
    FamilyMember,
    FamilyPermission,
    FamilyRole,
)


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FamilyOut(BaseModel):
    id: UUID
    name: str
    owner_user_id: UUID

    model_config = {"from_attributes": True}


class MemberOut(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    permissions: dict[str, bool]


class PermissionUpdate(BaseModel):
    permission_key: str
    allowed: bool


class FamilyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_family(self, user_id: UUID, data: FamilyCreate) -> Family:
        family = Family(name=data.name, owner_user_id=user_id)
        self._session.add(family)
        await self._session.flush()
        member = FamilyMember(family_id=family.id, user_id=user_id, role=FamilyRole.OWNER)
        self._session.add(member)
        await self._session.flush()
        await self._seed_permissions(family.id, member)
        return family

    async def _seed_permissions(self, family_id: UUID, member: FamilyMember) -> None:
        defaults = DEFAULT_PERMISSIONS.get(FamilyRole(member.role), {})
        for key, allowed in defaults.items():
            self._session.add(
                FamilyPermission(
                    family_id=family_id,
                    member_id=member.id,
                    permission_key=key,
                    allowed=allowed,
                )
            )
        await self._session.flush()

    async def list_families(self, user_id: UUID) -> list[Family]:
        result = await self._session.execute(
            select(Family)
            .join(FamilyMember, FamilyMember.family_id == Family.id)
            .where(FamilyMember.user_id == user_id)
        )
        return list(result.scalars().unique().all())

    async def get_members(self, user_id: UUID, family_id: UUID) -> list[MemberOut]:
        await self._require_member(user_id, family_id)
        result = await self._session.execute(
            select(FamilyMember).where(FamilyMember.family_id == family_id)
        )
        members = list(result.scalars().all())
        out: list[MemberOut] = []
        for m in members:
            perms = await self._permissions_map(m.id)
            out.append(MemberOut(id=m.id, user_id=m.user_id, role=m.role, permissions=perms))
        return out

    async def update_permission(
        self, actor_id: UUID, family_id: UUID, member_id: UUID, body: PermissionUpdate
    ) -> MemberOut:
        actor = await self._require_member(actor_id, family_id)
        if actor.role not in {FamilyRole.OWNER, FamilyRole.PARENT}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        member = await self._session.get(FamilyMember, member_id)
        if member is None or member.family_id != family_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found")

        result = await self._session.execute(
            select(FamilyPermission).where(
                FamilyPermission.member_id == member_id,
                FamilyPermission.permission_key == body.permission_key,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = FamilyPermission(
                family_id=family_id,
                member_id=member_id,
                permission_key=body.permission_key,
                allowed=body.allowed,
            )
            self._session.add(row)
        else:
            row.allowed = body.allowed
        await self._session.flush()
        return MemberOut(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            permissions=await self._permissions_map(member.id),
        )

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

    async def _permissions_map(self, member_id: UUID) -> dict[str, bool]:
        result = await self._session.execute(
            select(FamilyPermission).where(FamilyPermission.member_id == member_id)
        )
        return {p.permission_key: p.allowed for p in result.scalars().all()}
