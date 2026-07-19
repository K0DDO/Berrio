"""User profile — finance prefs for Berrio Score context."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.users.models import User

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileOut(BaseModel):
    display_name: str
    monthly_income: Decimal | None = None
    monthly_obligations: Decimal | None = None
    monthly_savings_target: Decimal | None = None
    ignore_receipt_time_default: bool = False


class UserProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    monthly_income: Decimal | None = None
    monthly_obligations: Decimal | None = None
    monthly_savings_target: Decimal | None = None
    ignore_receipt_time_default: bool | None = None


@router.get("/me/profile", response_model=UserProfileOut)
async def get_profile(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileOut:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfileOut(
        display_name=user.display_name,
        monthly_income=user.monthly_income,
        monthly_obligations=user.monthly_obligations,
        monthly_savings_target=user.monthly_savings_target,
        ignore_receipt_time_default=user.ignore_receipt_time_default,
    )


@router.patch("/me/profile", response_model=UserProfileOut)
async def patch_profile(
    body: UserProfilePatch,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileOut:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.display_name is not None:
        user.display_name = body.display_name.strip()
    if body.monthly_income is not None:
        user.monthly_income = body.monthly_income
    if body.monthly_obligations is not None:
        user.monthly_obligations = body.monthly_obligations
    if body.monthly_savings_target is not None:
        user.monthly_savings_target = body.monthly_savings_target
    if body.ignore_receipt_time_default is not None:
        user.ignore_receipt_time_default = body.ignore_receipt_time_default
    await session.commit()
    await session.refresh(user)
    return UserProfileOut(
        display_name=user.display_name,
        monthly_income=user.monthly_income,
        monthly_obligations=user.monthly_obligations,
        monthly_savings_target=user.monthly_savings_target,
        ignore_receipt_time_default=user.ignore_receipt_time_default,
    )
