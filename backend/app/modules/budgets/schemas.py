from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BudgetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    limit_amount: Decimal = Field(gt=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    period_type: str = Field(default="MONTH")
    period_start: date
    period_end: date | None = None
    category_id: UUID | None = None
    family_id: UUID | None = None


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    limit_amount: Decimal | None = Field(default=None, gt=0)
    period_end: date | None = None
    category_id: UUID | None = None
    status: str | None = None


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    family_id: UUID | None
    name: str
    category_id: UUID | None
    limit_amount: Decimal
    currency: str
    period_type: str
    period_start: date
    period_end: date | None
    status: str
    spent_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    usage_pct: float = 0.0
    over_budget: bool = False
