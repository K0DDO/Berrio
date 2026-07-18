from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    decrypt_email,
    encrypt_email,
    generate_opaque_token,
    generate_refresh_token,
    hash_email,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenPairResponse,
    UserPublic,
)
from app.modules.users.models import User


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repo = AuthRepository(session)
        self._audit = AuditService(session)

    async def register(
        self,
        data: RegisterRequest,
        *,
        user_agent: str | None = None,
        ip_hash: str | None = None,
    ) -> TokenPairResponse:
        email_h = hash_email(data.email)
        existing = await self._repo.get_user_by_email_hash(email_h)
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

        user = User(
            email_hash=email_h,
            email_enc=encrypt_email(data.email),
            password_hash=hash_password(data.password),
            display_name=data.display_name.strip() or data.email.split("@")[0],
            is_active=True,
            email_verified_at=None,
        )
        await self._repo.create_user(user)
        tokens = await self._issue_token_pair(
            user,
            device_id=data.device_id,
            device_name=data.device_name,
            user_agent=user_agent,
            ip_hash=ip_hash,
        )
        await self._audit.record(
            action="auth.register",
            actor_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            ip_hash=ip_hash,
            metadata={"device_id": data.device_id},
        )
        # Prep verification token (email send later)
        await self._create_email_verification_token(user.id)
        await self._session.commit()
        return tokens

    async def login(
        self,
        data: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_hash: str | None = None,
    ) -> TokenPairResponse:
        user = await self._repo.get_user_by_email_hash(hash_email(data.email))
        if user is None or not verify_password(data.password, user.password_hash):
            await self._audit.record(
                action="auth.login_failed",
                ip_hash=ip_hash,
                metadata={"email_hash_prefix": hash_email(data.email)[:12]},
            )
            await self._session.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account disabled")

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password)

        tokens = await self._issue_token_pair(
            user,
            device_id=data.device_id,
            device_name=data.device_name,
            user_agent=user_agent,
            ip_hash=ip_hash,
        )
        await self._audit.record(
            action="auth.login",
            actor_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            ip_hash=ip_hash,
            metadata={"device_id": data.device_id},
        )
        await self._session.commit()
        return tokens

    async def refresh(
        self,
        *,
        refresh_token: str,
        device_id: str,
        user_agent: str | None = None,
        ip_hash: str | None = None,
    ) -> TokenPairResponse:
        stored = await self._repo.get_refresh_by_hash(hash_token(refresh_token))
        if stored is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if stored.device_id != device_id:
            await self._repo.revoke_refresh(stored)
            await self._audit.record(
                action="auth.refresh_device_mismatch",
                actor_user_id=stored.user_id,
                entity_type="refresh_token",
                entity_id=stored.id,
                ip_hash=ip_hash,
                metadata={"expected_device": stored.device_id, "got_device": device_id},
            )
            await self._session.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Device mismatch")

        if stored.revoked_at is not None:
            # Possible reuse attack — revoke all sessions
            await self._repo.revoke_all_for_user(stored.user_id)
            await self._audit.record(
                action="auth.refresh_reuse_detected",
                actor_user_id=stored.user_id,
                entity_type="refresh_token",
                entity_id=stored.id,
                ip_hash=ip_hash,
            )
            await self._session.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            await self._repo.revoke_refresh(stored)
            await self._session.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        user = await self._repo.get_user_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User inactive")

        new_raw = generate_refresh_token()
        new_row = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_raw),
            device_id=device_id,
            device_name=stored.device_name,
            user_agent=user_agent or stored.user_agent,
            ip_hash=ip_hash,
            expires_at=datetime.now(UTC)
            + timedelta(days=self._settings.refresh_token_expire_days),
        )
        await self._repo.add_refresh_token(new_row)
        await self._repo.revoke_refresh(stored, replaced_by_id=new_row.id)

        access = create_access_token(user_id=user.id)
        await self._audit.record(
            action="auth.refresh",
            actor_user_id=user.id,
            entity_type="refresh_token",
            entity_id=new_row.id,
            ip_hash=ip_hash,
            metadata={"device_id": device_id},
        )
        await self._session.commit()
        return TokenPairResponse(
            access_token=access,
            refresh_token=new_raw,
            expires_in=self._settings.access_token_expire_minutes * 60,
            user=self._to_public(user),
        )

    async def logout(
        self,
        *,
        refresh_token: str,
        device_id: str,
        user_id: UUID,
        ip_hash: str | None = None,
    ) -> MessageResponse:
        stored = await self._repo.get_refresh_by_hash(hash_token(refresh_token))
        if (
            stored is not None
            and stored.user_id == user_id
            and stored.device_id == device_id
            and stored.revoked_at is None
        ):
            await self._repo.revoke_refresh(stored)
            await self._audit.record(
                action="auth.logout",
                actor_user_id=user_id,
                entity_type="refresh_token",
                entity_id=stored.id,
                ip_hash=ip_hash,
                metadata={"device_id": device_id},
            )
            await self._session.commit()
        return MessageResponse(message="Logged out")

    async def revoke_all(self, user_id: UUID, *, ip_hash: str | None = None) -> MessageResponse:
        count = await self._repo.revoke_all_for_user(user_id)
        await self._audit.record(
            action="auth.revoke_all",
            actor_user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            ip_hash=ip_hash,
            metadata={"revoked_count": count},
        )
        await self._session.commit()
        return MessageResponse(message="All sessions revoked", detail=f"revoked={count}")

    async def me(self, user_id: UUID) -> UserPublic:
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
        return self._to_public(user)

    async def request_email_verification(self, user_id: UUID) -> MessageResponse:
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.email_verified_at is not None:
            return MessageResponse(message="Email already verified")

        raw = await self._create_email_verification_token(user_id)
        await self._audit.record(
            action="auth.email_verification_requested",
            actor_user_id=user_id,
            entity_type="user",
            entity_id=user_id,
        )
        await self._session.commit()

        if not self._settings.email_verification_enabled:
            return MessageResponse(
                message="Verification token created (email delivery not configured)",
                detail=f"dev_token={raw}" if self._settings.debug else None,
            )
        return MessageResponse(message="Verification email queued")

    async def confirm_email_verification(self, token: str) -> MessageResponse:
        row = await self._repo.get_email_verification_by_hash(hash_token(token))
        if row is None or row.used_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Verification token expired")

        user = await self._repo.get_user_by_id(row.user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

        row.used_at = datetime.now(UTC)
        user.email_verified_at = datetime.now(UTC)
        await self._audit.record(
            action="auth.email_verified",
            actor_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
        )
        await self._session.commit()
        return MessageResponse(message="Email verified")

    async def request_password_reset(self, email: str) -> MessageResponse:
        """Always return generic message to avoid email enumeration."""
        user = await self._repo.get_user_by_email_hash(hash_email(email))
        detail = None
        if user is not None:
            raw = generate_opaque_token()
            token = PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC)
                + timedelta(hours=self._settings.password_reset_expire_hours),
            )
            await self._repo.add_password_reset_token(token)
            await self._audit.record(
                action="auth.password_reset_requested",
                actor_user_id=user.id,
                entity_type="user",
                entity_id=user.id,
            )
            await self._session.commit()
            if self._settings.debug and not self._settings.password_reset_enabled:
                detail = f"dev_token={raw}"

        return MessageResponse(
            message="If the account exists, reset instructions were issued",
            detail=detail,
        )

    async def confirm_password_reset(self, token: str, new_password: str) -> MessageResponse:
        row = await self._repo.get_password_reset_by_hash(hash_token(token))
        if row is None or row.used_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Reset token expired")

        user = await self._repo.get_user_by_id(row.user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

        row.used_at = datetime.now(UTC)
        user.password_hash = hash_password(new_password)
        await self._repo.revoke_all_for_user(user.id)
        await self._audit.record(
            action="auth.password_reset_completed",
            actor_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
        )
        await self._session.commit()
        return MessageResponse(message="Password updated")

    async def _create_email_verification_token(self, user_id: UUID) -> str:
        raw = generate_opaque_token()
        token = EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self._settings.email_verification_expire_hours),
        )
        await self._repo.add_email_verification_token(token)
        return raw

    async def _issue_token_pair(
        self,
        user: User,
        *,
        device_id: str,
        device_name: str | None,
        user_agent: str | None,
        ip_hash: str | None,
    ) -> TokenPairResponse:
        raw_refresh = generate_refresh_token()
        refresh_row = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_hash=ip_hash,
            expires_at=datetime.now(UTC)
            + timedelta(days=self._settings.refresh_token_expire_days),
        )
        await self._repo.add_refresh_token(refresh_row)
        access = create_access_token(user_id=user.id)
        return TokenPairResponse(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self._settings.access_token_expire_minutes * 60,
            user=self._to_public(user),
        )

    def _to_public(self, user: User) -> UserPublic:
        return UserPublic(
            id=user.id,
            email=decrypt_email(user.email_enc),
            display_name=user.display_name,
            email_verified=user.email_verified_at is not None,
            created_at=user.created_at,
        )
