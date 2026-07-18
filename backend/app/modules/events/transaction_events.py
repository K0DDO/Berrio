"""Transaction domain events (Stage 7+)."""

from app.modules.events.base import DomainEvent


class TransactionCreatedEvent(DomainEvent):
    event_type: str = "transaction.created"


class TransactionMatchedEvent(DomainEvent):
    event_type: str = "transaction.matched"
