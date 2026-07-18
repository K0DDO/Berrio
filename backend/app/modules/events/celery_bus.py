import structlog

from app.modules.events.base import DomainEvent
from app.modules.events.bus import EventBus

logger = structlog.get_logger(__name__)


class CeleryRedisEventBus:
    """
    MVP EventBus: enqueue Celery tasks named by event_type.

    Workers subscribe via task routes. No direct module coupling.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    async def publish(self, event: DomainEvent) -> None:
        if not self._enabled:
            logger.debug("eventbus.disabled", event_type=event.event_type)
            return

        # Stage 1: log-only stub. Celery dispatch wired when workers land.
        logger.info(
            "eventbus.publish",
            event_type=event.event_type,
            event_id=str(event.event_id),
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
        )
        # Future:
        # from app.workers.celery_app import celery_app
        # celery_app.send_task(f"events.{event.event_type}", args=[event.model_dump(mode='json')])

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)


def get_event_bus() -> EventBus:
    return CeleryRedisEventBus(enabled=True)
