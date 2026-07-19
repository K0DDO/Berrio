"""
Berrio Score — financial health (0–100) with explainable factors.

Considers income, obligations, category mix, savings intent, and data quality.
Avoids shaming food spend when income is low.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.categories.models import Category
from app.modules.financial_health.models import FinancialScore
from app.modules.receipts.models import Receipt, ReceiptStatus
from app.modules.users.models import User

_FOOD_HINTS = ("еда", "продукт", "food", "cafe", "grocery", "dairy", "delivery")
_ENTERTAIN_HINTS = ("развлеч", "entertainment", "кофе", "cafe")
_SUB_HINTS = ("подписк", "subscription")
_HOUSING_HINTS = ("дом", "жиль", "home", "rent", "квартир")


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
        income = obligations = savings_target = None
        if self._session is not None:
            user = await self._session.get(User, user_id)
            if user is not None:
                income = user.monthly_income
                obligations = user.monthly_obligations
                savings_target = user.monthly_savings_target

        if receipts is None and self._session is not None:
            receipts, total_spend = await self._load_month_spend(user_id)

        spend = total_spend if total_spend is not None else Decimal("0")
        receipt_count = len(receipts or [])
        cat_shares = await self._category_shares(receipts or [], spend)

        positive: list[str] = []
        negative: list[str] = []
        score = 55

        # Data completeness
        if receipt_count >= 5:
            positive.append(f"регулярный учёт покупок ({receipt_count} чеков)")
            score += 8
        elif receipt_count > 0:
            positive.append(f"есть данные о покупках ({receipt_count} чеков)")
            score += 4
        else:
            negative.append("мало данных для оценки — добавьте чеки или выписку")
            score -= 12

        if income is None or income <= 0:
            negative.append("не указан доход — оценка приблизительная")
            score -= 5
            # Absolute spend heuristics only
            if spend > Decimal("50000"):
                negative.append(f"высокие расходы за период: {spend} ₽")
                score -= 8
            elif 0 < spend < Decimal("20000"):
                positive.append(f"умеренные расходы: {spend} ₽")
                score += 6
        else:
            spend_ratio = float(spend / income) if income > 0 else 0.0
            food_share = cat_shares.get("food", 0.0)
            ent_share = cat_shares.get("entertainment", 0.0)
            sub_share = cat_shares.get("subscriptions", 0.0)

            if spend_ratio <= 0.7:
                positive.append(f"расходы {spend_ratio:.0%} дохода — под контролем")
                score += 12
            elif spend_ratio <= 0.9:
                positive.append(f"расходы {spend_ratio:.0%} дохода")
                score += 4
            else:
                negative.append(f"расходы {spend_ratio:.0%} дохода — выше комфортного уровня")
                score -= 12

            free = income - spend - (obligations or Decimal("0"))
            if obligations and obligations > 0:
                obl_ratio = float(obligations / income)
                if obl_ratio <= 0.4:
                    positive.append(f"обязательные платежи {obl_ratio:.0%} дохода")
                    score += 6
                else:
                    negative.append(f"обязательные платежи высоки: {obl_ratio:.0%} дохода")
                    score -= 8

            if savings_target and savings_target > 0:
                if free >= savings_target:
                    positive.append("удаётся откладывать на цель накоплений")
                    score += 10
                else:
                    negative.append("цель накоплений пока не достигается из свободного остатка")
                    score -= 6

            # Food context: don't shame low income
            if food_share >= 0.4:
                if income < Decimal("60000"):
                    negative.append(
                        "еда занимает большую долю бюджета — основная проблема скорее "
                        f"в уровне дохода ({income} ₽), а не в «лишних» тратах на еду"
                    )
                    score -= 3
                else:
                    negative.append(
                        f"еда {food_share:.0%} расходов — выше ориентира 25–30%; "
                        "можно пересмотреть доставку и импульсивные покупки"
                    )
                    score -= 8
            elif food_share > 0:
                positive.append(f"доля еды {food_share:.0%} — в разумных пределах")
                score += 4

            if ent_share >= 0.2 and income >= Decimal("60000"):
                negative.append(
                    f"развлечения {ent_share:.0%} расходов — есть запас для оптимизации"
                )
                score -= 5
            elif ent_share > 0 and ent_share < 0.15:
                positive.append("развлечения без перекоса")
                score += 3

            if sub_share > 0 and sub_share < 0.05:
                positive.append("подписки под контролем")
                score += 4
            elif sub_share >= 0.08:
                negative.append(f"подписки {sub_share:.0%} — стоит пересмотреть список")
                score -= 4

            if free > 0:
                positive.append(f"свободный остаток ≈ {free.quantize(Decimal('1'))} ₽")
                score += 5

        score = max(0, min(100, score))
        factors = {
            "positive": positive,
            "negative": negative,
            "income": str(income) if income is not None else None,
            "spend": str(spend.quantize(Decimal("0.01"))),
            "receipt_count": receipt_count,
            "category_shares": {k: round(v, 4) for k, v in cat_shares.items()},
        }

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

    async def _category_shares(self, receipts: list, spend: Decimal) -> dict[str, float]:
        if spend <= 0 or not receipts:
            return {}
        cat_ids = {i.category_id for r in receipts for i in r.items if i.category_id}
        names: dict[UUID, str] = {}
        if cat_ids and self._session is not None:
            result = await self._session.execute(select(Category).where(Category.id.in_(cat_ids)))
            names = {c.id: f"{c.slug} {c.name}".lower() for c in result.scalars().all()}

        buckets = {
            "food": Decimal("0"),
            "entertainment": Decimal("0"),
            "subscriptions": Decimal("0"),
            "housing": Decimal("0"),
            "other": Decimal("0"),
        }
        for receipt in receipts:
            for item in receipt.items:
                amount = item.sum or Decimal("0")
                label = (
                    names.get(item.category_id, (item.name_raw or "").lower())
                    if item.category_id
                    else (item.name_raw or "").lower()
                )
                if any(h in label for h in _FOOD_HINTS):
                    buckets["food"] += amount
                elif any(h in label for h in _ENTERTAIN_HINTS):
                    buckets["entertainment"] += amount
                elif any(h in label for h in _SUB_HINTS):
                    buckets["subscriptions"] += amount
                elif any(h in label for h in _HOUSING_HINTS):
                    buckets["housing"] += amount
                else:
                    buckets["other"] += amount

        return {k: float(v / spend) for k, v in buckets.items() if v > 0}

    async def _load_month_spend(self, user_id: UUID) -> tuple[list, Decimal]:
        assert self._session is not None
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(Receipt.user_id == user_id, Receipt.status == ReceiptStatus.DONE)
        )
        receipts = list(result.scalars().all())
        total = Decimal("0")
        for receipt in receipts:
            for item in receipt.items:
                total += item.sum or Decimal("0")
        return receipts, total
