from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.budgets.models import Budget, BudgetStatus
from app.modules.budgets.schemas import BudgetCreate, BudgetOut, BudgetUpdate
from app.modules.events import get_event_bus
from app.modules.events.budget_events import BudgetThresholdExceededEvent
from app.modules.notifications.service import NotificationService
from app.modules.receipts.models import Receipt


def _period_end(budget: Budget) -> date | None:
    return budget.period_end


class BudgetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)
        self._notifications = NotificationService(session)

    async def create(self, user_id: UUID, body: BudgetCreate) -> BudgetOut:
        budget = Budget(
            user_id=user_id,
            family_id=body.family_id,
            name=body.name,
            category_id=body.category_id,
            limit_amount=body.limit_amount,
            currency=body.currency.upper(),
            period_type=body.period_type.upper(),
            period_start=body.period_start,
            period_end=body.period_end,
            status=BudgetStatus.ACTIVE,
        )
        self._session.add(budget)
        await self._session.flush()
        await self._audit.record(
            action="budget.create",
            actor_user_id=user_id,
            entity_type="budget",
            entity_id=budget.id,
            family_id=body.family_id,
        )
        return await self._to_out(budget, [user_id])

    async def list_for_users(self, user_ids: list[UUID]) -> list[BudgetOut]:
        result = await self._session.execute(
            select(Budget)
            .where(Budget.user_id.in_(user_ids), Budget.status == BudgetStatus.ACTIVE)
            .order_by(Budget.created_at.desc())
        )
        return [await self._to_out(b, user_ids) for b in result.scalars().all()]

    async def get(self, user_ids: list[UUID], budget_id: UUID) -> BudgetOut:
        budget = await self._get(user_ids, budget_id)
        return await self._to_out(budget, user_ids)

    async def update(
        self,
        user_ids: list[UUID],
        actor_id: UUID,
        budget_id: UUID,
        body: BudgetUpdate,
    ) -> BudgetOut:
        budget = await self._get(user_ids, budget_id)
        data = body.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(budget, key, value)
        await self._session.flush()
        await self._audit.record(
            action="budget.update",
            actor_user_id=actor_id,
            entity_type="budget",
            entity_id=budget.id,
            family_id=budget.family_id,
        )
        return await self._to_out(budget, user_ids)

    async def archive(self, user_ids: list[UUID], actor_id: UUID, budget_id: UUID) -> BudgetOut:
        budget = await self._get(user_ids, budget_id)
        budget.status = BudgetStatus.ARCHIVED
        await self._session.flush()
        await self._audit.record(
            action="budget.archive",
            actor_user_id=actor_id,
            entity_type="budget",
            entity_id=budget.id,
            family_id=budget.family_id,
        )
        return await self._to_out(budget, user_ids)

    async def check_thresholds(self, user_ids: list[UUID], budget_id: UUID) -> BudgetOut:
        """Recompute spend and emit explainable budget alerts (80% / 100%)."""
        budget = await self._get(user_ids, budget_id)
        out = await self._to_out(budget, user_ids)
        drafts = self._notifications.rules.budget_monitoring(
            user_id=budget.user_id,
            family_id=budget.family_id,
            budget_id=budget.id,
            budget_name=budget.name,
            spent=out.spent_amount,
            limit_amount=out.limit_amount,
            currency=budget.currency,
        )
        if drafts:
            await self._notifications.dispatch_many(drafts)
            if out.over_budget:
                await get_event_bus().publish(
                    BudgetThresholdExceededEvent(
                        actor_user_id=budget.user_id,
                        payload={
                            "budget_id": str(budget.id),
                            "spent": str(out.spent_amount),
                            "limit": str(out.limit_amount),
                        },
                    )
                )
        return out

    async def _spent_amount(self, budget: Budget, scope_user_ids: list[UUID]) -> Decimal:
        start = datetime.combine(budget.period_start, time.min, tzinfo=timezone.utc)
        end_date = _period_end(budget)
        stmt = select(func.coalesce(func.sum(Receipt.total_amount), 0)).where(
            Receipt.user_id.in_(scope_user_ids),
            Receipt.total_amount.is_not(None),
            Receipt.purchased_at.is_not(None),
            Receipt.purchased_at >= start,
        )
        if end_date is not None:
            end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
            stmt = stmt.where(Receipt.purchased_at <= end)
        # Category filter deferred until receipt items are joined in analytics.
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return Decimal(str(value))

    async def _to_out(self, budget: Budget, scope_user_ids: list[UUID]) -> BudgetOut:
        spent = await self._spent_amount(budget, scope_user_ids)
        remaining = budget.limit_amount - spent
        usage = float((spent / budget.limit_amount) * 100) if budget.limit_amount > 0 else 0.0
        return BudgetOut(
            id=budget.id,
            user_id=budget.user_id,
            family_id=budget.family_id,
            name=budget.name,
            category_id=budget.category_id,
            limit_amount=budget.limit_amount,
            currency=budget.currency,
            period_type=budget.period_type,
            period_start=budget.period_start,
            period_end=budget.period_end,
            status=budget.status,
            spent_amount=spent,
            remaining_amount=remaining,
            usage_pct=round(usage, 2),
            over_budget=spent > budget.limit_amount,
        )

    async def _get(self, user_ids: list[UUID], budget_id: UUID) -> Budget:
        result = await self._session.execute(
            select(Budget).where(Budget.id == budget_id, Budget.user_id.in_(user_ids))
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Budget not found")
        return budget
