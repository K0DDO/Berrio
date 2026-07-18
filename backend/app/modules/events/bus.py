from typing import Protocol, runtime_checkable

from app.modules.events.base import DomainEvent


@runtime_checkable
class EventBus(Protocol):
    """
    Abstraction over the message bus.

    MVP: CeleryRedisEventBus
    Future: RabbitMqEventBus / KafkaEventBus — swap via DI, same contract.
    """

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to interested subscribers."""

    async def publish_many(self, events: list[DomainEvent]) -> None:
        """Publish multiple events (order preserved best-effort)."""
