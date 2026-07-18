"""Explainable financial alert rules.

Domain signal -> draft NotificationCreate (human-readable why).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.modules.notifications.models import NotificationSeverity, NotificationType
from app.modules.notifications.schemas import NotificationCreate


class NotificationRulesEngine:
    """Pure rules - no I/O. NotificationService persists and dispatches."""

    def budget_monitoring(
        self,
        *,
        user_id: UUID,
        family_id: UUID | None,
        budget_id: UUID,
        budget_name: str,
        spent: Decimal,
        limit_amount: Decimal,
        currency: str = "RUB",
    ) -> list[NotificationCreate]:
        if limit_amount <= 0:
            return []
        usage = (spent / limit_amount) * Decimal("100")
        drafts: list[NotificationCreate] = []

        if usage >= Decimal("100"):
            drafts.append(
                NotificationCreate(
                    user_id=user_id,
                    family_id=family_id,
                    type=NotificationType.BUDGET_EXCEEDED,
                    severity=NotificationSeverity.CRITICAL,
                    title="Budget exceeded",
                    message=(
                        f"{budget_name}: spent {spent} of {limit_amount} {currency} "
                        f"({usage:.0f}%). Limit exhausted."
                    ),
                    payload={
                        "budget_id": str(budget_id),
                        "spent": str(spent),
                        "limit": str(limit_amount),
                        "usage_pct": float(usage),
                        "rule": "spent >= 100%",
                        "explanation": "Spend reached or exceeded the budget limit.",
                    },
                    dedupe_key=f"budget_exceeded:{budget_id}",
                )
            )
        elif usage >= Decimal("80"):
            drafts.append(
                NotificationCreate(
                    user_id=user_id,
                    family_id=family_id,
                    type=NotificationType.BUDGET_WARNING,
                    severity=NotificationSeverity.WARNING,
                    title="Budget almost exhausted",
                    message=(
                        f"{budget_name}: already {usage:.0f}% of limit "
                        f"({spent} of {limit_amount} {currency})."
                    ),
                    payload={
                        "budget_id": str(budget_id),
                        "spent": str(spent),
                        "limit": str(limit_amount),
                        "usage_pct": float(usage),
                        "rule": "spent >= 80%",
                        "explanation": "Spend crossed the 80% warning threshold.",
                    },
                    dedupe_key=f"budget_warn:{budget_id}",
                )
            )
        return drafts

    def price_change(
        self,
        *,
        user_id: UUID,
        product_name: str,
        variant_id: UUID,
        old_price: Decimal,
        new_price: Decimal,
        store_name: str | None = None,
        currency: str = "RUB",
    ) -> NotificationCreate | None:
        if old_price <= 0 or new_price <= old_price:
            return None
        delta_pct = ((new_price - old_price) / old_price) * Decimal("100")
        if delta_pct < Decimal("5"):
            return None
        store = f" at {store_name}" if store_name else ""
        return NotificationCreate(
            user_id=user_id,
            type=NotificationType.PRICE_CHANGE,
            severity=NotificationSeverity.WARNING if delta_pct >= 20 else NotificationSeverity.INFO,
            title="Price increased",
            message=(
                f"{product_name}{store}: {old_price} RUB -> {new_price} RUB " f"(+{delta_pct:.0f}%)"
            ),
            payload={
                "product_variant_id": str(variant_id),
                "old_price": str(old_price),
                "new_price": str(new_price),
                "delta_pct": float(delta_pct),
                "store_name": store_name,
                "rule": "same ProductVariant price increased",
                "explanation": f"Price rose by {delta_pct:.0f}% vs last observed purchase.",
            },
            dedupe_key=f"price:{variant_id}:{old_price}:{new_price}",
        )

    def goal_progress(
        self,
        *,
        user_id: UUID,
        family_id: UUID | None,
        goal_id: UUID,
        goal_name: str,
        current: Decimal,
        target: Decimal,
        currency: str = "RUB",
    ) -> NotificationCreate | None:
        if target <= 0:
            return None
        progress = (current / target) * Decimal("100")
        remaining = Decimal("100") - progress
        if current >= target:
            return NotificationCreate(
                user_id=user_id,
                family_id=family_id,
                type=NotificationType.GOAL_PROGRESS,
                severity=NotificationSeverity.INFO,
                title="Goal reached",
                message=f"{goal_name}: {current}/{target} {currency} - done!",
                payload={
                    "goal_id": str(goal_id),
                    "progress_pct": float(progress),
                    "remaining_pct": 0.0,
                    "rule": "current >= target",
                    "explanation": "Goal target amount was reached.",
                },
                dedupe_key=f"goal_done:{goal_id}",
            )
        if remaining <= Decimal("20") and remaining > 0:
            return NotificationCreate(
                user_id=user_id,
                family_id=family_id,
                type=NotificationType.GOAL_PROGRESS,
                severity=NotificationSeverity.INFO,
                title="Almost there",
                message=(
                    f"{remaining:.0f}% left to goal '{goal_name}' "
                    f"({current}/{target} {currency})"
                ),
                payload={
                    "goal_id": str(goal_id),
                    "progress_pct": float(progress),
                    "remaining_pct": float(remaining),
                    "rule": "remaining <= 20%",
                    "explanation": "Less than or equal to 20% of the goal amount remains.",
                },
                dedupe_key=f"goal_near:{goal_id}",
            )
        return None

    def unusual_spending(
        self,
        *,
        user_id: UUID,
        receipt_id: UUID,
        amount: Decimal,
        average: Decimal,
        store_name: str | None = None,
        currency: str = "RUB",
        multiplier: Decimal = Decimal("2"),
    ) -> NotificationCreate | None:
        if average <= 0 or amount < average * multiplier:
            return None
        store = store_name or "store"
        ratio = amount / average
        return NotificationCreate(
            user_id=user_id,
            type=NotificationType.UNUSUAL_SPENDING,
            severity=NotificationSeverity.WARNING,
            title="Unusual purchase",
            message=(
                f"{store}: {amount} {currency} - {ratio:.1f}x above "
                f"your average receipt ({average} {currency})."
            ),
            payload={
                "receipt_id": str(receipt_id),
                "amount": str(amount),
                "average": str(average),
                "ratio": float(ratio),
                "rule": f"amount >= {multiplier}x rolling average",
                "explanation": "Receipt total is significantly above your recent average spend.",
            },
            dedupe_key=f"unusual:{receipt_id}",
        )
