from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.categories.models import Category
from app.modules.financial_health.service import FinancialHealthService
from app.modules.receipts.models import Receipt, ReceiptStatus


class PeriodQuery(BaseModel):
    period: str = Field(default="month")  # day|week|month|year|all


class CategorySpendOut(BaseModel):
    category_id: UUID | None
    category_name: str
    amount: Decimal
    share: float


class AnalyticsSummaryOut(BaseModel):
    period: str
    period_start: date | None
    period_end: date | None
    total_spend: Decimal
    receipt_count: int
    by_category: list[CategorySpendOut]
    berrio_score: int | None = None
    score_factors: dict | None = None


def _period_bounds(period: str) -> tuple[datetime | None, datetime | None]:
    now = datetime.now(UTC)
    end = now
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    elif period == "year":
        start = now - timedelta(days=365)
    elif period == "all":
        return None, None
    else:
        start = now - timedelta(days=30)
    return start, end


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._health = FinancialHealthService(session)

    async def summary(self, user_id: UUID, *, period: str = "month") -> AnalyticsSummaryOut:
        start, end = _period_bounds(period)
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(
                Receipt.user_id == user_id,
                Receipt.status == ReceiptStatus.DONE,
            )
        )
        receipts = list(result.scalars().all())
        if start is not None:
            filtered = []
            for r in receipts:
                ts = r.purchased_at or r.created_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                if start <= ts <= (end or datetime.now(UTC)):
                    filtered.append(r)
            receipts = filtered

        cat_rows = await self._session.execute(select(Category))
        cat_names = {c.id: c.name for c in cat_rows.scalars().all()}

        totals: dict[UUID | None, Decimal] = {}
        total = Decimal("0.00")
        for receipt in receipts:
            for item in receipt.items:
                amount = item.sum or Decimal("0")
                total += amount
                key = item.category_id
                totals[key] = totals.get(key, Decimal("0")) + amount

        by_category: list[CategorySpendOut] = []
        for cat_id, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True):
            share = float(amount / total) if total > 0 else 0.0
            by_category.append(
                CategorySpendOut(
                    category_id=cat_id,
                    category_name=cat_names.get(cat_id, "Без категории") if cat_id else "Без категории",
                    amount=amount.quantize(Decimal("0.01")),
                    share=round(share, 4),
                )
            )

        health = await self._health.compute(user_id, receipts=receipts, total_spend=total)

        return AnalyticsSummaryOut(
            period=period,
            period_start=start.date() if start else None,
            period_end=end.date() if end else None,
            total_spend=total.quantize(Decimal("0.01")),
            receipt_count=len(receipts),
            by_category=by_category,
            berrio_score=health.score,
            score_factors=health.factors,
        )
