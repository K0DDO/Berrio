"""Dashboard aggregator — read-only composition of domain services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai.service import AiService
from app.modules.budgets.models import Budget, BudgetStatus
from app.modules.categories.models import Category
from app.modules.dashboard.schemas import (
    AiRecommendationPreview,
    CategoryTrendOut,
    DashboardGoalOut,
    DashboardNotificationOut,
    DashboardOut,
    DashboardScoreOut,
    DashboardSpendOut,
)
from app.modules.financial_health.service import FinancialHealthService
from app.modules.goals.models import FinancialGoal, GoalStatus
from app.modules.notifications.service import NotificationService
from app.modules.receipts.models import Receipt, ReceiptStatus


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._health = FinancialHealthService(session)
        self._notifications = NotificationService(session)
        self._ai = AiService(session)

    async def build(self, user_id: UUID) -> DashboardOut:
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 1:
            prev_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            prev_start = month_start.replace(month=month_start.month - 1)
        prev_end = month_start - timedelta(microseconds=1)

        receipts = await self._done_receipts(user_id)
        current = [r for r in receipts if self._in_range(r, month_start, now)]
        previous = [r for r in receipts if self._in_range(r, prev_start, prev_end)]

        current_spend = self._spend(current)
        previous_spend = self._spend(previous)
        change_pct = None
        if previous_spend > 0:
            change_pct = float(
                ((current_spend - previous_spend) / previous_spend * Decimal("100")).quantize(
                    Decimal("0.1")
                )
            )

        budget_limit = await self._active_budget_limit(user_id)
        health = await self._health.compute(user_id, receipts=current, total_spend=current_spend)

        category_trends = await self._category_trends(current, previous)
        goals = await self._active_goals(user_id)
        notes = await self._notifications.list_for_user(user_id, limit=5)
        ai_preview = await self._ai_preview(user_id)

        return DashboardOut(
            berrio_score=DashboardScoreOut(score=health.score, factors=health.factors),
            spending=DashboardSpendOut(
                current_month=current_spend,
                previous_month=previous_spend,
                change_pct=change_pct,
                budget_limit=budget_limit,
            ),
            category_trends=category_trends,
            active_goals=goals,
            recent_notifications=[
                DashboardNotificationOut(
                    id=n.id,
                    type=n.type if isinstance(n.type, str) else n.type.value,
                    title=n.title,
                    message=n.message,
                    severity=n.severity if isinstance(n.severity, str) else n.severity.value,
                    created_at=n.created_at,
                    read_at=n.read_at,
                )
                for n in notes
            ],
            ai_recommendation=ai_preview,
        )

    async def _done_receipts(self, user_id: UUID) -> list[Receipt]:
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(Receipt.user_id == user_id, Receipt.status == ReceiptStatus.DONE)
        )
        return list(result.scalars().all())

    @staticmethod
    def _in_range(receipt: Receipt, start: datetime, end: datetime) -> bool:
        ts = receipt.purchased_at or receipt.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return start <= ts <= end

    @staticmethod
    def _spend(receipts: list[Receipt]) -> Decimal:
        total = Decimal("0")
        for r in receipts:
            if r.total_amount is not None:
                total += r.total_amount
            else:
                for item in r.items:
                    total += item.sum or Decimal("0")
        return total.quantize(Decimal("0.01"))

    async def _active_budget_limit(self, user_id: UUID) -> Decimal | None:
        result = await self._session.execute(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.status == BudgetStatus.ACTIVE,
            )
        )
        budgets = list(result.scalars().all())
        if not budgets:
            return None
        return sum((b.limit_amount for b in budgets), Decimal("0")).quantize(Decimal("0.01"))

    async def _category_trends(
        self, current: list[Receipt], previous: list[Receipt]
    ) -> list[CategoryTrendOut]:
        cat_rows = await self._session.execute(select(Category))
        names = {c.id: c.name for c in cat_rows.scalars().all()}

        def by_cat(receipts: list[Receipt]) -> dict[UUID | None, Decimal]:
            totals: dict[UUID | None, Decimal] = {}
            for r in receipts:
                for item in r.items:
                    key = item.category_id
                    totals[key] = totals.get(key, Decimal("0")) + (item.sum or Decimal("0"))
            return totals

        cur = by_cat(current)
        prev = by_cat(previous)
        keys = set(cur) | set(prev)
        trends: list[CategoryTrendOut] = []
        for key in keys:
            c_amt = cur.get(key, Decimal("0")).quantize(Decimal("0.01"))
            p_amt = prev.get(key, Decimal("0")).quantize(Decimal("0.01"))
            if c_amt == 0 and p_amt == 0:
                continue
            change = None
            direction = "flat"
            if p_amt > 0:
                change = float(((c_amt - p_amt) / p_amt * Decimal("100")).quantize(Decimal("0.1")))
                if change > 2:
                    direction = "up"
                elif change < -2:
                    direction = "down"
            elif c_amt > 0:
                direction = "up"
                change = 100.0
            trends.append(
                CategoryTrendOut(
                    category_id=key,
                    category_name=names.get(key, "Other") if key else "Other",
                    current_amount=c_amt,
                    previous_amount=p_amt,
                    change_pct=change,
                    direction=direction,
                )
            )
        trends.sort(key=lambda t: t.current_amount, reverse=True)
        return trends[:8]

    async def _active_goals(self, user_id: UUID) -> list[DashboardGoalOut]:
        result = await self._session.execute(
            select(FinancialGoal)
            .where(
                FinancialGoal.user_id == user_id,
                FinancialGoal.status == GoalStatus.ACTIVE,
            )
            .order_by(FinancialGoal.created_at.desc())
            .limit(5)
        )
        out: list[DashboardGoalOut] = []
        for g in result.scalars().all():
            pct = 0.0
            if g.target_amount > 0:
                pct = float(
                    min(
                        Decimal("100"),
                        (g.current_amount / g.target_amount) * Decimal("100"),
                    )
                )
            out.append(
                DashboardGoalOut(
                    id=g.id,
                    name=g.name,
                    progress_pct=round(pct, 1),
                    current_amount=g.current_amount,
                    target_amount=g.target_amount,
                    currency=g.currency,
                    status=g.status,
                )
            )
        return out

    async def _ai_preview(self, user_id: UUID) -> AiRecommendationPreview | None:
        try:
            insights = await self._ai.insights(user_id, period="month")
        except Exception:  # noqa: BLE001
            return None
        if not insights:
            return None
        first = insights[0]
        return AiRecommendationPreview(title=first.title, body=first.body, kind=first.kind)
