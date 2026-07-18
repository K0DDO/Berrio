"""Receipt-related domain events (payloads filled in Stage 3)."""

from uuid import UUID

from app.modules.events.base import DomainEvent


class ReceiptCreatedEvent(DomainEvent):
    event_type: str = "receipt.created"

    @classmethod
    def build(cls, *, receipt_id: UUID, user_id: UUID, **extra: object) -> "ReceiptCreatedEvent":
        return cls(
            actor_user_id=user_id,
            payload={"receipt_id": str(receipt_id), **extra},
        )


class ReceiptFetchedEvent(DomainEvent):
    event_type: str = "receipt.fetched"
