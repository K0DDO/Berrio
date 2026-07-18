"""
Berrio Score — financial health (0–100) with explainable factors.

Computation in Stage 5; AI explanation in Stage 6.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class FinancialHealthResult:
    user_id: UUID
    score: int
    factors: dict[str, Any] = field(default_factory=dict)


class FinancialHealthService:
    """Stub calculator."""

    async def compute(self, user_id: UUID) -> FinancialHealthResult:
        return FinancialHealthResult(
            user_id=user_id,
            score=0,
            factors={"positive": [], "negative": [], "status": "not_computed"},
        )
