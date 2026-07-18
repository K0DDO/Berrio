from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    target_amount: Decimal = Field(gt=0)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    deadline: date | None = None
    category: str | None = Field(default=None, max_length=80)
    family_id: UUID | None = None
    notes: str | None = None


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    target_amount: Decimal | None = Field(default=None, gt=0)
    current_amount: Decimal | None = Field(default=None, ge=0)
    deadline: date | None = None
    category: str | None = None
    status: str | None = None
    notes: str | None = None


class GoalProgressUpdate(BaseModel):
    current_amount: Decimal = Field(ge=0)


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    family_id: UUID | None
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: date | None
    category: str | None
    status: str
    notes: str | None
    progress_pct: float = 0.0
