from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)
    device_id: str = Field(min_length=8, max_length=128)
    device_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if value.isdigit() or value.isalpha():
            raise ValueError("Password must include letters and numbers (or symbols)")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str = Field(min_length=8, max_length=128)
    device_name: str | None = Field(default=None, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str
    device_id: str = Field(min_length=8, max_length=128)


class LogoutRequest(BaseModel):
    refresh_token: str
    device_id: str = Field(min_length=8, max_length=128)


class RevokeAllRequest(BaseModel):
    """Revoke all refresh tokens for the authenticated user."""


class UserPublic(BaseModel):
    id: UUID
    email: str
    display_name: str
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
