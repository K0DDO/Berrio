from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.fns_client import FnsClient, get_fns_client
from app.modules.audit.service import AuditService
from app.modules.events import get_event_bus
from app.modules.events.receipt_events import ReceiptCreatedEvent, ReceiptFetchedEvent
from app.modules.receipts.models import Receipt, ReceiptItem, ReceiptStatus
from app.modules.receipts.repository import ReceiptRepository
from app.modules.receipts.schemas import ReceiptOut, ReceiptScanRequest


class ReceiptService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        fns_client: FnsClient | None = None,
    ) -> None:
        self._session = session
        self._repo = ReceiptRepository(session)
        self._audit = AuditService(session)
        self._bus = get_event_bus()
        self._fns = fns_client or get_fns_client()

    async def scan(self, user_id: UUID, data: ReceiptScanRequest) -> ReceiptOut:
        existing = await self._repo.find_by_fingerprint(
            user_id=user_id, fn=data.fn, fd=data.fd, fp=data.fp
        )
        if existing is not None:
            return self._to_out(existing)

        receipt = await self._repo.create_pending(
            user_id=user_id,
            fn=data.fn,
            fd=data.fd,
            fp=data.fp,
            purchased_at=data.purchased_at,
            total_amount=data.total_amount,
        )
        await self._audit.record(
            action="receipt.scan",
            actor_user_id=user_id,
            entity_type="receipt",
            entity_id=receipt.id,
            metadata={"fn": data.fn, "fd": data.fd, "fp": data.fp},
        )
        await self._bus.publish(
            ReceiptCreatedEvent.build(receipt_id=receipt.id, user_id=user_id)
        )
        await self._session.commit()

        # Stage 3: process inline via stub FNS (Celery wire stays for later scale)
        await self.process_receipt(receipt.id, user_id)
        refreshed = await self._repo.get_by_id(receipt.id, user_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    async def process_receipt(self, receipt_id: UUID, user_id: UUID) -> ReceiptOut:
        receipt = await self._repo.get_by_id(receipt_id, user_id)
        if receipt is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        if receipt.status == ReceiptStatus.DONE:
            return self._to_out(receipt)

        receipt.status = ReceiptStatus.FETCHING
        await self._repo.save(receipt)
        await self._session.commit()

        try:
            data = await self._fns.fetch(
                fn=receipt.fn,
                fd=receipt.fd,
                fp=receipt.fp,
                purchased_at=receipt.purchased_at,
                total_amount=receipt.total_amount,
            )
            receipt.store_name = data.store_name
            receipt.store_inn = data.store_inn
            receipt.purchased_at = data.purchased_at
            receipt.total_amount = data.total_amount
            receipt.status = ReceiptStatus.DONE
            receipt.error_message = None

            # Clear previous items if re-fetch
            receipt.items.clear()
            for line in data.items:
                receipt.items.append(
                    ReceiptItem(
                        name_raw=line.name,
                        qty=line.qty,
                        price=line.price,
                        sum=line.sum,
                    )
                )
            await self._repo.save(receipt)
            await self._bus.publish(
                ReceiptFetchedEvent(
                    actor_user_id=user_id,
                    payload={"receipt_id": str(receipt.id), "items": len(data.items)},
                )
            )
            await self._audit.record(
                action="receipt.fetched",
                actor_user_id=user_id,
                entity_type="receipt",
                entity_id=receipt.id,
                metadata={"store": data.store_name, "items": len(data.items)},
            )
            await self._session.commit()
        except Exception as exc:  # noqa: BLE001 — convert to failed status
            receipt.status = ReceiptStatus.FAILED
            receipt.error_message = str(exc)[:500]
            await self._repo.save(receipt)
            await self._session.commit()
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch receipt from FNS"
            ) from exc

        refreshed = await self._repo.get_by_id(receipt_id, user_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    async def get(self, user_id: UUID, receipt_id: UUID) -> ReceiptOut:
        receipt = await self._repo.get_by_id(receipt_id, user_id)
        if receipt is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        return self._to_out(receipt)

    async def list(self, user_id: UUID, *, limit: int = 50, offset: int = 0) -> tuple[list[ReceiptOut], int]:
        rows, total = await self._repo.list_for_user(user_id, limit=limit, offset=offset)
        return [self._to_out(r) for r in rows], total

    def _to_out(self, receipt: Receipt) -> ReceiptOut:
        return ReceiptOut.model_validate(receipt)
