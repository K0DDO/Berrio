from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReconciliationMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    receipt_id: UUID
    transaction_id: UUID
    score: Decimal
    confidence: Decimal = Decimal("0")
    status: str
    reasons: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    decided_at: datetime | None


class ReconciliationRunResult(BaseModel):
    created: int
    suggestions: list[ReconciliationMatchOut]
