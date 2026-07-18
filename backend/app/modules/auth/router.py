from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.modules.auth.dependencies import (
    client_ip_hash,
    get_auth_service,
    get_current_user_id,
    get_optional_user_id,
)
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmBody,
    PasswordResetRequestBody,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserPublic,
    VerifyEmailRequest,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPairResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.register(
        body,
        user_agent=request.headers.get("user-agent"),
        ip_hash=client_ip_hash(request),
    )


@router.post("/login", response_model=TokenPairResponse)
async def login(
    body: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.login(
        body,
        user_agent=request.headers.get("user-agent"),
        ip_hash=client_ip_hash(request),
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.refresh(
        refresh_token=body.refresh_token,
        device_id=body.device_id,
        user_agent=request.headers.get("user-agent"),
        ip_hash=client_ip_hash(request),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: LogoutRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
) -> MessageResponse:
    return await service.logout(
        refresh_token=body.refresh_token,
        device_id=body.device_id,
        user_id=user_id,
        ip_hash=client_ip_hash(request),
    )


@router.post("/revoke-all", response_model=MessageResponse)
async def revoke_all(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> MessageResponse:
    return await service.revoke_all(user_id, ip_hash=client_ip_hash(request))


@router.get("/me", response_model=UserPublic)
async def me(
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> UserPublic:
    return await service.me(user_id)


@router.post("/verify-email/request", response_model=MessageResponse)
async def request_email_verification(
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> MessageResponse:
    return await service.request_email_verification(user_id)


@router.post("/verify-email/confirm", response_model=MessageResponse)
async def confirm_email_verification(
    body: VerifyEmailRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.confirm_email_verification(body.token)


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    body: PasswordResetRequestBody,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.request_password_reset(body.email)


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    body: PasswordResetConfirmBody,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.confirm_password_reset(body.token, body.new_password)
