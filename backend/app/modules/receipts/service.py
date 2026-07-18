from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.fns_client import FnsClient, FnsReceiptData, get_fns_client
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
from app.modules.receipts.recognition import (
    CONFIDENCE_AUTO_SAVE_THRESHOLD,
    ReceiptRecognitionPipeline,
)
from app.modules.receipts.recognition.models import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    ConfidenceField,
    ReceiptConfirmRequest,
    RecognizedItem,
    StructuredReceipt,
)
from app.modules.receipts.recognition.validator import (
    looks_like_hallucinated_stub,
    validate_structured,
)
from app.modules.receipts.repository import ReceiptRepository
from app.modules.receipts.schemas import ReceiptItemOut, ReceiptOut, ReceiptScanRequest


class ReceiptService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        fns_client: FnsClient | None = None,
        recognition: ReceiptRecognitionPipeline | None = None,
    ) -> None:
        self._session = session
        self._repo = ReceiptRepository(session)
        self._audit = AuditService(session)
        self._bus = get_event_bus()
        self._fns = fns_client or get_fns_client()
        self._categorization = CategorizationService(session)
        self._products = ProductService(session)
        self._notifications = NotificationService(session)
        self._recognition = recognition or ReceiptRecognitionPipeline()

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
            structured = self._structured_from_fns(data)
            validation = validate_structured(structured)
            if looks_like_hallucinated_stub(data.store_name, [i.name for i in data.items]):
                validation.ok = False
                validation.requires_confirmation = True
                validation.status = ReceiptStatus.NEEDS_CONFIRMATION
                validation.reasons.append("Подозрение на галлюцинацию stub (магазин+товары)")
                structured.requires_confirmation = True
                structured.reason = validation.reasons[-1]

            auto_ok = (
                validation.ok
                and not data.incomplete
                and structured.overall_confidence >= CONFIDENCE_AUTO_SAVE_THRESHOLD
                and not structured.requires_confirmation
            )

            receipt.store_name = data.store_name
            receipt.store_inn = data.store_inn
            receipt.purchased_at = data.purchased_at
            if data.total_amount is not None:
                receipt.total_amount = data.total_amount
            receipt.error_message = (
                None
                if auto_ok
                else (data.incomplete_reason or structured.reason or "; ".join(validation.reasons))[
                    :500
                ]
            )
            receipt.recognition_json = json.dumps(
                {
                    **structured.to_meta_dict(),
                    "validation_reasons": validation.reasons,
                    "fns_incomplete": data.incomplete,
                    "source_confidence": data.source_confidence,
                },
                ensure_ascii=False,
                default=str,
            )

            receipt.items.clear()
            if auto_ok:
                receipt.status = ReceiptStatus.DONE
                for line in data.items:
                    receipt.items.append(
                        ReceiptItem(
                            name_raw=line.name,
                            qty=line.qty,
                            price=line.price,
                            sum=line.sum,
                        )
                    )
                await self._categorization.apply_to_receipt_items(
                    list(receipt.items), user_id=user_id
                )
                for item in receipt.items:
                    await self._products.resolve_for_receipt_item(
                        item,
                        user_id=user_id,
                        store_name=receipt.store_name,
                        purchased_at=receipt.purchased_at,
                        category_id=item.category_id,
                    )
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
            else:
                receipt.status = ReceiptStatus.NEEDS_CONFIRMATION
                await self._audit.record(
                    action="receipt.needs_confirmation",
                    actor_user_id=user_id,
                    entity_type="receipt",
                    entity_id=receipt.id,
                    metadata={
                        "reasons": validation.reasons,
                        "incomplete": data.incomplete,
                    },
                )

            await self._repo.save(receipt)
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

    async def analyze_text(self, user_id: UUID, body: AnalyzeTextRequest) -> AnalyzeTextResponse:
        structured, validation = self._recognition.analyze_text(body.raw_text)
        if not body.persist:
            return AnalyzeTextResponse(
                success=structured.success,
                requires_confirmation=validation.requires_confirmation
                or structured.requires_confirmation,
                reason=structured.reason,
                structured=structured,
                receipt_id=None,
                status=None,
            )

        fn = body.fn or f"ocr-{uuid4().hex[:16]}"
        fd = body.fd or f"ocr-{uuid4().hex[:16]}"
        fp = body.fp or f"ocr-{uuid4().hex[:16]}"
        existing = await self._repo.find_by_fingerprint(user_id=user_id, fn=fn, fd=fd, fp=fp)
        if existing is not None:
            return AnalyzeTextResponse(
                success=existing.status == ReceiptStatus.DONE,
                requires_confirmation=existing.status == ReceiptStatus.NEEDS_CONFIRMATION,
                reason=existing.error_message,
                structured=structured,
                receipt_id=str(existing.id),
                status=existing.status,
            )

        auto_ok = (
            validation.ok
            and structured.success
            and not structured.requires_confirmation
            and structured.overall_confidence >= CONFIDENCE_AUTO_SAVE_THRESHOLD
            and structured.amount.value is not None
        )

        receipt = await self._repo.create_pending(
            user_id=user_id,
            fn=fn,
            fd=fd,
            fp=fp,
            purchased_at=datetime.now(UTC),
            total_amount=structured.amount.value,
        )
        # Reload with items relationship to avoid async lazy-load
        receipt = await self._repo.get_by_id(receipt.id, user_id)
        assert receipt is not None
        receipt.store_name = structured.merchant.value
        receipt.recognition_json = json.dumps(
            {
                **structured.to_meta_dict(),
                "validation_reasons": validation.reasons,
            },
            ensure_ascii=False,
            default=str,
        )

        if auto_ok:
            receipt.status = ReceiptStatus.DONE
            receipt.error_message = None
            await self._apply_structured_items(receipt, structured.items, user_id)
            await self._audit.record(
                action="receipt.ocr_saved",
                actor_user_id=user_id,
                entity_type="receipt",
                entity_id=receipt.id,
                metadata={"merchant": receipt.store_name},
            )
            await self._maybe_unusual_spending(receipt, user_id)
            await self._check_active_budgets(user_id)
        else:
            receipt.status = ReceiptStatus.NEEDS_CONFIRMATION
            receipt.error_message = (
                structured.reason
                or (validation.reasons[0] if validation.reasons else None)
                or "Не удалось уверенно распознать чек"
            )[:500]
            await self._audit.record(
                action="receipt.ocr_needs_confirmation",
                actor_user_id=user_id,
                entity_type="receipt",
                entity_id=receipt.id,
                metadata={"reasons": validation.reasons},
            )

        await self._repo.save(receipt)
        await self._session.commit()
        return AnalyzeTextResponse(
            success=auto_ok,
            requires_confirmation=not auto_ok,
            reason=None if auto_ok else receipt.error_message,
            structured=structured,
            receipt_id=str(receipt.id),
            status=receipt.status,
        )

    async def confirm(
        self, user_id: UUID, receipt_id: UUID, body: ReceiptConfirmRequest
    ) -> ReceiptOut:
        receipt = await self._repo.get_by_id(receipt_id, user_id)
        if receipt is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        if receipt.status == ReceiptStatus.DONE and not body.confirm_as_is:
            return await self._to_out(receipt)

        if body.store_name is not None:
            receipt.store_name = body.store_name.strip()[:255] or None
        if body.total_amount is not None:
            receipt.total_amount = body.total_amount
        if body.purchased_at:
            parsed = self._parse_user_dt(body.purchased_at)
            if parsed is not None:
                receipt.purchased_at = parsed

        items = body.items
        if not items and body.confirm_as_is and receipt.recognition_json:
            try:
                meta = json.loads(receipt.recognition_json)
                raw_items = meta.get("items") or []
                items = [RecognizedItem.model_validate(i) for i in raw_items]
            except Exception:  # noqa: BLE001
                items = []

        if receipt.total_amount is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="total_amount is required to confirm a receipt",
            )

        receipt.items.clear()
        await self._session.flush()
        await self._apply_structured_items(receipt, items, user_id)

        if body.category_slug and receipt.items:
            cat = await self._session.scalar(
                select(Category).where(Category.slug == body.category_slug)
            )
            if cat is not None:
                for item in receipt.items:
                    item.category_id = cat.id

        receipt.status = ReceiptStatus.DONE
        receipt.error_message = None
        meta = {}
        if receipt.recognition_json:
            try:
                meta = json.loads(receipt.recognition_json)
            except json.JSONDecodeError:
                meta = {}
        meta["user_confirmed"] = True
        meta["confirmed_store"] = receipt.store_name
        meta["confirmed_amount"] = str(receipt.total_amount)
        receipt.recognition_json = json.dumps(meta, ensure_ascii=False, default=str)

        await self._repo.save(receipt)
        await self._audit.record(
            action="receipt.confirmed",
            actor_user_id=user_id,
            entity_type="receipt",
            entity_id=receipt.id,
            metadata={"store": receipt.store_name, "amount": str(receipt.total_amount)},
        )
        await self._maybe_unusual_spending(receipt, user_id)
        await self._check_active_budgets(user_id)
        await self._session.commit()

        refreshed = await self._repo.get_by_id(receipt_id, user_id)
        assert refreshed is not None
        return await self._to_out(refreshed)

    async def _apply_structured_items(
        self,
        receipt: Receipt,
        items: list[RecognizedItem],
        user_id: UUID,
    ) -> None:
        for line in items:
            if not line.name.strip():
                continue
            price = line.price
            line_sum = line.sum
            if line_sum is None and price is not None:
                line_sum = (price * line.qty).quantize(Decimal("0.01"))
            if price is None and line_sum is not None:
                price = line_sum
            if price is None and receipt.total_amount is not None and len(items) == 1:
                price = receipt.total_amount
                line_sum = receipt.total_amount
            if price is None or line_sum is None:
                continue
            receipt.items.append(
                ReceiptItem(
                    name_raw=line.name[:512],
                    qty=line.qty or Decimal("1"),
                    price=price,
                    sum=line_sum,
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

    @staticmethod
    def _structured_from_fns(data: FnsReceiptData) -> StructuredReceipt:
        conf = float(data.source_confidence)
        items = [
            RecognizedItem(
                name=i.name,
                qty=i.qty,
                price=i.price,
                sum=i.sum,
                confidence=conf if i.name else 0.0,
            )
            for i in data.items
        ]
        merchant_conf = conf if data.store_name else 0.1
        amount_conf = conf if data.total_amount is not None else 0.1
        overall = conf
        if data.incomplete:
            overall = min(overall, 0.45)
        return StructuredReceipt(
            merchant=ConfidenceField(value=data.store_name, confidence=merchant_conf),
            amount=ConfidenceField(value=data.total_amount, confidence=amount_conf),
            items=items,
            raw_ocr_text="",
            overall_confidence=overall,
            requires_confirmation=data.incomplete or overall < CONFIDENCE_AUTO_SAVE_THRESHOLD,
            success=not data.incomplete and data.total_amount is not None,
            reason=data.incomplete_reason,
        )

    @staticmethod
    def _parse_user_dt(value: str) -> datetime | None:
        text = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None

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

        recognition = None
        if receipt.recognition_json:
            try:
                recognition = json.loads(receipt.recognition_json)
            except json.JSONDecodeError:
                recognition = None

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
            requires_confirmation=receipt.status == ReceiptStatus.NEEDS_CONFIRMATION,
            recognition=recognition,
            items=items_out,
            created_at=receipt.created_at,
        )
