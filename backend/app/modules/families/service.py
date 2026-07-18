from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_opaque_token, hash_email, hash_token
from app.modules.audit.service import AuditService
from app.modules.families.models import (
    DEFAULT_PERMISSIONS,
    Family,
    FamilyInvite,
    FamilyInviteStatus,
    FamilyMember,
    FamilyPermission,
    FamilyRole,
)
from app.modules.families.permission_checker import (
    FamilyPermissionChecker,
    FamilyPermissionKey,
)
from app.modules.users.models import User

_INVITE_RATE: dict[str, list[float]] = {}
_INVITE_RATE_MAX = 20  # per hour per user


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


class InviteCreate(BaseModel):
    email: EmailStr | None = None
    role: str = Field(default=FamilyRole.PARENT, pattern="^(PARENT|CHILD)$")
    expires_hours: int = Field(default=72, ge=1, le=168)


class InviteOut(BaseModel):
    id: UUID
    family_id: UUID
    role: str
    status: str
    expires_at: datetime
    has_email_lock: bool
    # Returned only once on create — never stored plaintext.
    token: str | None = None


class InviteAccept(BaseModel):
    token: str = Field(min_length=16, max_length=128)


class FamilyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)
        self._checker = FamilyPermissionChecker(session)

    async def create_family(self, user_id: UUID, data: FamilyCreate) -> Family:
        family = Family(name=data.name, owner_user_id=user_id)
        self._session.add(family)
        await self._session.flush()
        member = FamilyMember(family_id=family.id, user_id=user_id, role=FamilyRole.OWNER)
        self._session.add(member)
        await self._session.flush()
        await self._seed_permissions(family.id, member)
        await self._audit.record(
            action="family.create",
            actor_user_id=user_id,
            entity_type="family",
            entity_id=family.id,
            family_id=family.id,
        )
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
        await self._audit.record(
            action="family.permission_update",
            actor_user_id=actor_id,
            entity_type="family_member",
            entity_id=member_id,
            family_id=family_id,
            metadata={"permission_key": body.permission_key, "allowed": body.allowed},
        )
        return MemberOut(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            permissions=await self._permissions_map(member.id),
        )

    async def create_invite(self, actor_id: UUID, family_id: UUID, body: InviteCreate) -> InviteOut:
        self._enforce_invite_rate(actor_id)
        await self._checker.assert_can(
            actor_id=actor_id,
            family_id=family_id,
            permission=FamilyPermissionKey.CAN_INVITE_MEMBERS,
        )
        if body.role == FamilyRole.OWNER:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot invite as OWNER")

        raw = generate_opaque_token()
        email_h = hash_email(str(body.email)) if body.email else None
        invite = FamilyInvite(
            family_id=family_id,
            invited_by_user_id=actor_id,
            email_hash=email_h,
            role=body.role,
            token_hash=hash_token(raw),
            status=FamilyInviteStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(hours=body.expires_hours),
        )
        self._session.add(invite)
        await self._session.flush()
        await self._audit.record(
            action="family.invite_create",
            actor_user_id=actor_id,
            entity_type="family_invite",
            entity_id=invite.id,
            family_id=family_id,
            metadata={"role": body.role, "email_locked": email_h is not None},
        )
        return InviteOut(
            id=invite.id,
            family_id=invite.family_id,
            role=invite.role,
            status=invite.status,
            expires_at=invite.expires_at,
            has_email_lock=email_h is not None,
            token=raw,
        )

    async def list_invites(self, actor_id: UUID, family_id: UUID) -> list[InviteOut]:
        await self._checker.assert_can(
            actor_id=actor_id,
            family_id=family_id,
            permission=FamilyPermissionKey.CAN_INVITE_MEMBERS,
        )
        result = await self._session.execute(
            select(FamilyInvite)
            .where(FamilyInvite.family_id == family_id)
            .order_by(FamilyInvite.created_at.desc())
            .limit(50)
        )
        return [
            InviteOut(
                id=i.id,
                family_id=i.family_id,
                role=i.role,
                status=i.status,
                expires_at=i.expires_at,
                has_email_lock=i.email_hash is not None,
                token=None,
            )
            for i in result.scalars().all()
        ]

    async def revoke_invite(self, actor_id: UUID, family_id: UUID, invite_id: UUID) -> InviteOut:
        await self._checker.assert_can(
            actor_id=actor_id,
            family_id=family_id,
            permission=FamilyPermissionKey.CAN_INVITE_MEMBERS,
        )
        invite = await self._session.get(FamilyInvite, invite_id)
        if invite is None or invite.family_id != family_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invite not found")
        if invite.status != FamilyInviteStatus.PENDING:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invite is not pending")
        invite.status = FamilyInviteStatus.REVOKED
        await self._session.flush()
        await self._audit.record(
            action="family.invite_revoke",
            actor_user_id=actor_id,
            entity_type="family_invite",
            entity_id=invite.id,
            family_id=family_id,
        )
        return InviteOut(
            id=invite.id,
            family_id=invite.family_id,
            role=invite.role,
            status=invite.status,
            expires_at=invite.expires_at,
            has_email_lock=invite.email_hash is not None,
            token=None,
        )

    async def accept_invite(self, user_id: UUID, body: InviteAccept) -> MemberOut:
        token_h = hash_token(body.token)
        result = await self._session.execute(
            select(FamilyInvite).where(FamilyInvite.token_hash == token_h)
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invite not found")

        now = datetime.now(UTC)
        expires = (
            invite.expires_at if invite.expires_at.tzinfo else invite.expires_at.replace(tzinfo=UTC)
        )
        if invite.status != FamilyInviteStatus.PENDING or expires < now:
            if invite.status == FamilyInviteStatus.PENDING and expires < now:
                invite.status = FamilyInviteStatus.EXPIRED
                await self._session.flush()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invite expired or inactive")

        if invite.email_hash is not None:
            user = await self._session.get(User, user_id)
            if user is None or user.email_hash != invite.email_hash:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Invite is locked to a different email",
                )

        existing = await self._session.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == invite.family_id,
                FamilyMember.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Already a family member")

        member = FamilyMember(
            family_id=invite.family_id,
            user_id=user_id,
            role=invite.role,
        )
        self._session.add(member)
        await self._session.flush()
        await self._seed_permissions(invite.family_id, member)
        invite.status = FamilyInviteStatus.ACCEPTED
        invite.accepted_at = now
        invite.accepted_by_user_id = user_id
        await self._session.flush()
        await self._audit.record(
            action="family.invite_accept",
            actor_user_id=user_id,
            entity_type="family_invite",
            entity_id=invite.id,
            family_id=invite.family_id,
            metadata={"role": invite.role},
        )
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

    @staticmethod
    def _enforce_invite_rate(user_id: UUID) -> None:
        import time

        key = str(user_id)
        now = time.time()
        window = _INVITE_RATE.setdefault(key, [])
        _INVITE_RATE[key] = [t for t in window if now - t < 3600]
        if len(_INVITE_RATE[key]) >= _INVITE_RATE_MAX:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Invite rate limit exceeded",
            )
        _INVITE_RATE[key].append(now)
