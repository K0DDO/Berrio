from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.fns_client import FnsClient, get_fns_client
from app.modules.audit.service import AuditService
from app.modules.budgets.models import Budget, BudgetStatus
from app.modules.budgets.service import BudgetService
from app.modules.categories.models import Category
from app.modules.categorization.service import CategorizationService
from app.modules.events import get_event_bus
from app.modules.events.receipt_events import ReceiptCreatedEvent, ReceiptFetchedEvent
from app.modules.notifications.service import NotificationService
from app.modules.products.models import ProductPriceHistory
from app.modules.products.service import ProductService
from app.modules.receipts.models import Receipt, ReceiptItem, ReceiptStatus
from app.modules.receipts.repository import ReceiptRepository
from app.modules.receipts.schemas import ReceiptItemOut, ReceiptOut, ReceiptScanRequest


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
        self._categorization = CategorizationService(session)
        self._products = ProductService(session)
        self._notifications = NotificationService(session)

    async def scan(self, user_id: UUID, data: ReceiptScanRequest) -> ReceiptOut:
        existing = await self._repo.find_by_fingerprint(
            user_id=user_id, fn=data.fn, fd=data.fd, fp=data.fp
        )
        if existing is not None:
            return await self._to_out(existing)

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
        await self._bus.publish(ReceiptCreatedEvent.build(receipt_id=receipt.id, user_id=user_id))
        await self._session.commit()

        # Stage 3: process inline via stub FNS (Celery wire stays for later scale)
        await self.process_receipt(receipt.id, user_id)
        refreshed = await self._repo.get_by_id(receipt.id, user_id)
        assert refreshed is not None
        return await self._to_out(refreshed)

    async def process_receipt(self, receipt_id: UUID, user_id: UUID) -> ReceiptOut:
        receipt = await self._repo.get_by_id(receipt_id, user_id)
        if receipt is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        if receipt.status == ReceiptStatus.DONE:
            return await self._to_out(receipt)

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
            await self._categorization.apply_to_receipt_items(list(receipt.items), user_id=user_id)
            for item in receipt.items:
                await self._products.resolve_for_receipt_item(
                    item,
                    user_id=user_id,
                    store_name=receipt.store_name,
                    purchased_at=receipt.purchased_at,
                    category_id=item.category_id,
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
            await self._maybe_unusual_spending(receipt, user_id)
            await self._check_active_budgets(user_id)
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
        return await self._to_out(refreshed)

    async def _maybe_unusual_spending(self, receipt: Receipt, user_id: UUID) -> None:
        if receipt.total_amount is None:
            return
        result = await self._session.execute(
            select(func.avg(Receipt.total_amount)).where(
                Receipt.user_id == user_id,
                Receipt.id != receipt.id,
                Receipt.total_amount.is_not(None),
                Receipt.status == ReceiptStatus.DONE,
            )
        )
        avg = result.scalar_one_or_none()
        if avg is None:
            return
        draft = self._notifications.rules.unusual_spending(
            user_id=user_id,
            receipt_id=receipt.id,
            amount=receipt.total_amount,
            average=Decimal(str(avg)),
            store_name=receipt.store_name,
        )
        if draft is not None:
            await self._notifications.create_and_dispatch(draft)

    async def _check_active_budgets(self, user_id: UUID) -> None:
        result = await self._session.execute(
            select(Budget.id).where(
                Budget.user_id == user_id,
                Budget.status == BudgetStatus.ACTIVE,
            )
        )
        budget_service = BudgetService(self._session)
        for (budget_id,) in result.all():
            await budget_service.check_thresholds([user_id], budget_id)

    async def get(
        self, user_id: UUID, receipt_id: UUID, *, scope_user_ids: list[UUID] | None = None
    ) -> ReceiptOut:
        ids = scope_user_ids or [user_id]
        receipt = await self._repo.get_for_users(receipt_id, ids)
        if receipt is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        return await self._to_out(receipt)

    async def list(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        scope_user_ids: list[UUID] | None = None,
    ) -> tuple[list[ReceiptOut], int]:
        ids = scope_user_ids or [user_id]
        rows, total = await self._repo.list_for_users(ids, limit=limit, offset=offset)
        return [await self._to_out(r) for r in rows], total

    async def _to_out(self, receipt: Receipt) -> ReceiptOut:
        cat_ids = {i.category_id for i in receipt.items if i.category_id}
        cat_names: dict[UUID, str] = {}
        if cat_ids:
            result = await self._session.execute(select(Category).where(Category.id.in_(cat_ids)))
            cat_names = {c.id: c.name for c in result.scalars().all()}

        items_out: list[ReceiptItemOut] = []
        for item in receipt.items:
            prev_price = None
            change_pct = None
            if item.product_variant_id is not None and item.price is not None:
                hist = await self._session.execute(
                    select(ProductPriceHistory.price)
                    .where(ProductPriceHistory.product_variant_id == item.product_variant_id)
                    .order_by(ProductPriceHistory.purchased_at.desc())
                    .limit(2)
                )
                prices = list(hist.scalars().all())
                if len(prices) >= 2 and Decimal(str(prices[1])) > 0:
                    prev_price = Decimal(str(prices[1]))
                    change_pct = float(
                        ((item.price - prev_price) / prev_price * Decimal("100")).quantize(
                            Decimal("0.1")
                        )
                    )
            items_out.append(
                ReceiptItemOut(
                    id=item.id,
                    name_raw=item.name_raw,
                    qty=item.qty,
                    price=item.price,
                    sum=item.sum,
                    category_id=item.category_id,
                    category_name=cat_names.get(item.category_id) if item.category_id else None,
                    product_variant_id=item.product_variant_id,
                    previous_price=prev_price,
                    price_change_pct=change_pct,
                )
            )

        return ReceiptOut(
            id=receipt.id,
            fn=receipt.fn,
            fd=receipt.fd,
            fp=receipt.fp,
            status=receipt.status,
            purchased_at=receipt.purchased_at,
            total_amount=receipt.total_amount,
            store_name=receipt.store_name,
            store_inn=receipt.store_inn,
            error_message=receipt.error_message,
            items=items_out,
            created_at=receipt.created_at,
        )
