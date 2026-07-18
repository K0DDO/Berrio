"""Dashboard aggregation schemas — no persistence."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardScoreOut(BaseModel):
    score: int
    factors: dict[str, Any] = Field(default_factory=dict)


class DashboardSpendOut(BaseModel):
    current_month: Decimal
    previous_month: Decimal
    change_pct: float | None = None
    budget_limit: Decimal | None = None
    currency: str = "RUB"


class CategoryTrendOut(BaseModel):
    category_id: UUID | None = None
    category_name: str
    current_amount: Decimal
    previous_amount: Decimal
    change_pct: float | None = None
    direction: str  # up | down | flat


class DashboardGoalOut(BaseModel):
    id: UUID
    name: str
    progress_pct: float
    current_amount: Decimal
    target_amount: Decimal
    currency: str
    status: str


class DashboardNotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    severity: str
    created_at: date | Any
    read_at: Any = None


class AiRecommendationPreview(BaseModel):
    title: str
    body: str
    kind: str


class DashboardOut(BaseModel):
    berrio_score: DashboardScoreOut
    spending: DashboardSpendOut
    category_trends: list[CategoryTrendOut]
    active_goals: list[DashboardGoalOut]
    recent_notifications: list[DashboardNotificationOut]
    ai_recommendation: AiRecommendationPreview | None = None
