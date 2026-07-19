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


class MerchantSpendOut(BaseModel):
    store_name: str
    purchase_count: int
    amount: Decimal


class AnalyticsSummaryOut(BaseModel):
    period: str
    period_start: date | None
    period_end: date | None
    total_spend: Decimal
    receipt_count: int
    avg_receipt: Decimal | None = None
    previous_total_spend: Decimal | None = None
    previous_change_pct: float | None = None
    by_category: list[CategorySpendOut]
    top_merchants: list[MerchantSpendOut] = []
    berrio_score: int | None = None
    score_factors: dict | None = None


def _period_bounds(period: str) -> tuple[datetime | None, datetime | None]:
    """Calendar day / week / month / year (UTC), not rolling windows."""
    now = datetime.now(UTC)
    end = now
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        # Monday 00:00 UTC of the current ISO week
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "all":
        return None, None
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, end


def _previous_bounds(
    period: str, start: datetime | None, end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    if start is None or end is None:
        return None, None
    if period == "day":
        prev_start = start - timedelta(days=1)
        return prev_start, start
    if period == "week":
        prev_start = start - timedelta(days=7)
        return prev_start, start
    if period == "month":
        # Previous calendar month
        first_this = start
        last_prev = first_this - timedelta(seconds=1)
        prev_start = last_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return prev_start, first_this
    if period == "year":
        prev_start = start.replace(year=start.year - 1)
        return prev_start, start
    delta = end - start
    return start - delta, start


class DaySpendOut(BaseModel):
    day: date
    amount: Decimal


class AnalyticsTimeseriesOut(BaseModel):
    period: str
    period_start: date | None
    period_end: date | None
    points: list[DaySpendOut]


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._health = FinancialHealthService(session)

    async def summary(
        self,
        user_id: UUID,
        *,
        period: str = "month",
        scope_user_ids: list[UUID] | None = None,
    ) -> AnalyticsSummaryOut:
        start, end = _period_bounds(period)
        ids = scope_user_ids or [user_id]
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(
                Receipt.user_id.in_(ids),
                Receipt.status == ReceiptStatus.DONE,
            )
        )
        all_receipts = list(result.scalars().all())
        receipts = self._filter_period(all_receipts, start, end)

        cat_rows = await self._session.execute(select(Category))
        cat_names = {c.id: c.name for c in cat_rows.scalars().all()}

        totals: dict[UUID | None, Decimal] = {}
        total = Decimal("0.00")
        merchant_totals: dict[str, tuple[int, Decimal]] = {}
        for receipt in receipts:
            store = (receipt.store_name or "Без магазина").strip() or "Без магазина"
            receipt_sum = Decimal("0")
            for item in receipt.items:
                amount = item.sum or Decimal("0")
                total += amount
                receipt_sum += amount
                key = item.category_id
                totals[key] = totals.get(key, Decimal("0")) + amount
            cnt, amt = merchant_totals.get(store, (0, Decimal("0")))
            merchant_totals[store] = (cnt + 1, amt + (receipt.total_amount or receipt_sum))

        by_category: list[CategorySpendOut] = []
        for cat_id, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True):
            share = float(amount / total) if total > 0 else 0.0
            by_category.append(
                CategorySpendOut(
                    category_id=cat_id,
                    category_name=(
                        cat_names.get(cat_id, "Без категории") if cat_id else "Без категории"
                    ),
                    amount=amount.quantize(Decimal("0.01")),
                    share=round(share, 4),
                )
            )

        top_merchants = [
            MerchantSpendOut(
                store_name=name,
                purchase_count=cnt,
                amount=amt.quantize(Decimal("0.01")),
            )
            for name, (cnt, amt) in sorted(
                merchant_totals.items(), key=lambda x: x[1][1], reverse=True
            )[:8]
        ]

        prev_start, prev_end = _previous_bounds(period, start, end)
        prev_receipts = self._filter_period(all_receipts, prev_start, prev_end)
        previous_total = Decimal("0")
        for receipt in prev_receipts:
            for item in receipt.items:
                previous_total += item.sum or Decimal("0")

        change_pct = None
        if previous_total > 0:
            change_pct = float(
                ((total - previous_total) / previous_total * Decimal("100")).quantize(
                    Decimal("0.1")
                )
            )

        avg_receipt = None
        if receipts:
            avg_receipt = (total / Decimal(len(receipts))).quantize(Decimal("0.01"))

        health = await self._health.compute(user_id, receipts=receipts, total_spend=total)

        return AnalyticsSummaryOut(
            period=period,
            period_start=start.date() if start else None,
            period_end=end.date() if end else None,
            total_spend=total.quantize(Decimal("0.01")),
            receipt_count=len(receipts),
            avg_receipt=avg_receipt,
            previous_total_spend=previous_total.quantize(Decimal("0.01")),
            previous_change_pct=change_pct,
            by_category=by_category,
            top_merchants=top_merchants,
            berrio_score=health.score,
            score_factors=health.factors,
        )

    async def timeseries(
        self,
        user_id: UUID,
        *,
        period: str = "month",
        scope_user_ids: list[UUID] | None = None,
    ) -> AnalyticsTimeseriesOut:
        start, end = _period_bounds(period)
        ids = scope_user_ids or [user_id]
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(
                Receipt.user_id.in_(ids),
                Receipt.status == ReceiptStatus.DONE,
            )
        )
        receipts = self._filter_period(list(result.scalars().all()), start, end)
        by_day: dict[date, Decimal] = {}
        for receipt in receipts:
            ts = receipt.purchased_at or receipt.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            day = ts.date()
            day_sum = Decimal("0")
            for item in receipt.items:
                day_sum += item.sum or Decimal("0")
            if receipt.total_amount is not None and day_sum == 0:
                day_sum = receipt.total_amount
            by_day[day] = by_day.get(day, Decimal("0")) + day_sum

        # Fill empty days in the window for a continuous sparkline.
        points: list[DaySpendOut] = []
        if start is not None:
            cursor = start.date()
            last = (end or datetime.now(UTC)).date()
            while cursor <= last:
                points.append(
                    DaySpendOut(
                        day=cursor,
                        amount=by_day.get(cursor, Decimal("0")).quantize(Decimal("0.01")),
                    )
                )
                cursor += timedelta(days=1)
        else:
            for day in sorted(by_day):
                points.append(
                    DaySpendOut(
                        day=day,
                        amount=by_day[day].quantize(Decimal("0.01")),
                    )
                )

        return AnalyticsTimeseriesOut(
            period=period,
            period_start=start.date() if start else None,
            period_end=end.date() if end else None,
            points=points,
        )

    @staticmethod
    def _filter_period(
        receipts: list[Receipt],
        start: datetime | None,
        end: datetime | None,
    ) -> list[Receipt]:
        if start is None:
            return list(receipts)
        filtered = []
        for r in receipts:
            ts = r.purchased_at or r.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if start <= ts <= (end or datetime.now(UTC)):
                filtered.append(r)
        return filtered
