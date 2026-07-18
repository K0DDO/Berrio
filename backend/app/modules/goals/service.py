from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.events import get_event_bus
from app.modules.events.goal_events import GoalProgressUpdatedEvent
from app.modules.goals.models import FinancialGoal, GoalStatus
from app.modules.goals.schemas import GoalCreate, GoalOut, GoalProgressUpdate, GoalUpdate
from app.modules.notifications.service import NotificationService


def _progress_pct(current: Decimal, target: Decimal) -> float:
    if target <= 0:
        return 0.0
    return float(min(Decimal("100"), (current / target) * Decimal("100")))


def _to_out(goal: FinancialGoal) -> GoalOut:
    return GoalOut(
        id=goal.id,
        user_id=goal.user_id,
        family_id=goal.family_id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        currency=goal.currency,
        deadline=goal.deadline,
        category=goal.category,
        status=goal.status,
        notes=goal.notes,
        progress_pct=_progress_pct(goal.current_amount, goal.target_amount),
    )


class GoalService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)
        self._notifications = NotificationService(session)

    async def create(self, user_id: UUID, body: GoalCreate) -> GoalOut:
        goal = FinancialGoal(
            user_id=user_id,
            family_id=body.family_id,
            name=body.name,
            target_amount=body.target_amount,
            current_amount=body.current_amount,
            currency=body.currency.upper(),
            deadline=body.deadline,
            category=body.category,
            notes=body.notes,
            status=GoalStatus.ACTIVE,
        )
        self._session.add(goal)
        await self._session.flush()
        await self._audit.record(
            action="goal.create",
            actor_user_id=user_id,
            entity_type="financial_goal",
            entity_id=goal.id,
            family_id=body.family_id,
        )
        return _to_out(goal)

    async def list_for_users(self, user_ids: list[UUID]) -> list[GoalOut]:
        result = await self._session.execute(
            select(FinancialGoal)
            .where(FinancialGoal.user_id.in_(user_ids))
            .order_by(FinancialGoal.created_at.desc())
        )
        return [_to_out(g) for g in result.scalars().all()]

    async def get(self, user_ids: list[UUID], goal_id: UUID) -> GoalOut:
        goal = await self._get(user_ids, goal_id)
        return _to_out(goal)

    async def update(self, user_ids: list[UUID], actor_id: UUID, goal_id: UUID, body: GoalUpdate) -> GoalOut:
        goal = await self._get(user_ids, goal_id)
        data = body.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(goal, key, value)
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
        await self._session.flush()
        await self._audit.record(
            action="goal.update",
            actor_user_id=actor_id,
            entity_type="financial_goal",
            entity_id=goal.id,
            family_id=goal.family_id,
        )
        return _to_out(goal)

    async def update_progress(
        self,
        user_ids: list[UUID],
        actor_id: UUID,
        goal_id: UUID,
        body: GoalProgressUpdate,
    ) -> GoalOut:
        goal = await self._get(user_ids, goal_id)
        previous = goal.current_amount
        goal.current_amount = body.current_amount
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
        await self._session.flush()

        bus = get_event_bus()
        await bus.publish(
            GoalProgressUpdatedEvent(
                actor_user_id=actor_id,
                payload={
                    "goal_id": str(goal.id),
                    "previous": str(previous),
                    "current": str(goal.current_amount),
                    "target": str(goal.target_amount),
                },
            )
        )
        draft = self._notifications.rules.goal_progress(
            user_id=goal.user_id,
            family_id=goal.family_id,
            goal_id=goal.id,
            goal_name=goal.name,
            current=goal.current_amount,
            target=goal.target_amount,
            currency=goal.currency,
        )
        if draft is not None:
            await self._notifications.create_and_dispatch(draft)
        await self._audit.record(
            action="goal.progress",
            actor_user_id=actor_id,
            entity_type="financial_goal",
            entity_id=goal.id,
            family_id=goal.family_id,
            metadata={"current_amount": str(goal.current_amount)},
        )
        return _to_out(goal)

    async def archive(self, user_ids: list[UUID], actor_id: UUID, goal_id: UUID) -> GoalOut:
        goal = await self._get(user_ids, goal_id)
        goal.status = GoalStatus.ARCHIVED
        await self._session.flush()
        await self._audit.record(
            action="goal.archive",
            actor_user_id=actor_id,
            entity_type="financial_goal",
            entity_id=goal.id,
            family_id=goal.family_id,
        )
        return _to_out(goal)

    async def _get(self, user_ids: list[UUID], goal_id: UUID) -> FinancialGoal:
        result = await self._session.execute(
            select(FinancialGoal).where(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id.in_(user_ids),
            )
        )
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Goal not found")
        return goal
