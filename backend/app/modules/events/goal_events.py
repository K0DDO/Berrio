"""Goal domain events."""

from app.modules.events.base import DomainEvent


class GoalProgressUpdatedEvent(DomainEvent):
    event_type: str = "goal.progress_updated"
