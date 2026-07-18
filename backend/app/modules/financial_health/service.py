"""
Berrio Score — financial health (0–100) with explainable factors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.financial_health.models import FinancialScore


@dataclass(slots=True)
class FinancialHealthResult:
    user_id: UUID
    score: int
    factors: dict[str, Any] = field(default_factory=dict)


class FinancialHealthService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def compute(
        self,
        user_id: UUID,
        *,
        receipts: list | None = None,
        total_spend: Decimal | None = None,
    ) -> FinancialHealthResult:
        positive: list[str] = []
        negative: list[str] = []
        score = 70

        receipt_count = len(receipts or [])
        spend = total_spend if total_spend is not None else Decimal("0")

        if receipt_count > 0:
            positive.append("есть данные о покупках")
            score += 5
        else:
            negative.append("мало данных для оценки")
            score -= 15

        if spend == 0:
            positive.append("нет расходов за период")
            score += 5
        elif spend < Decimal("5000"):
            positive.append("умеренные расходы за период")
            score += 10
        elif spend > Decimal("30000"):
            negative.append("высокие расходы за период")
            score -= 15

        # Diversification proxy: many receipts → slightly healthier tracking habit
        if receipt_count >= 3:
            positive.append("регулярно учитываются покупки")
            score += 5

        score = max(0, min(100, score))
        factors = {"positive": positive, "negative": negative}

        if self._session is not None:
            row = FinancialScore(
                id=uuid4(),
                user_id=user_id,
                score=score,
                period_start=datetime.now(UTC).date(),
                period_end=datetime.now(UTC).date(),
                factors=factors,
            )
            self._session.add(row)
            await self._session.flush()

        return FinancialHealthResult(user_id=user_id, score=score, factors=factors)
