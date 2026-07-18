"""Budget domain events."""

from app.modules.events.base import DomainEvent


class BudgetThresholdExceededEvent(DomainEvent):
    event_type: str = "budget.threshold_exceeded"
