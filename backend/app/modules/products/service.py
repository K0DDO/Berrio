"""Product normalization — Product + Variant + price history."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.service import NotificationService
from app.modules.products.models import Product, ProductPriceHistory, ProductVariant
from app.modules.receipts.models import ReceiptItem

_VOLUME_RE = re.compile(
    r"(?P<num>\d+[.,]?\d*)\s*(?P<unit>мл|ml|л|l|г|g|кг|kg)\b",
    re.IGNORECASE,
)


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notifications = NotificationService(session)

    async def resolve_for_receipt_item(
        self,
        item: ReceiptItem,
        *,
        user_id: UUID,
        store_name: str | None,
        purchased_at,
        category_id: UUID | None,
    ) -> ProductVariant:
        brand, name, weight, volume, unit = self._parse_name(item.name_raw)
        product = await self._find_or_create_product(brand, name, category_id)
        variant = await self._find_or_create_variant(product.id, weight, volume, unit)
        item.product_variant_id = variant.id

        previous = await self._last_price(variant.id, user_id=user_id)
        if previous is not None and item.price is not None:
            display = f"{brand} {product.name}".strip() if brand else product.name
            draft = self._notifications.rules.price_change(
                user_id=user_id,
                product_name=display,
                variant_id=variant.id,
                old_price=previous,
                new_price=item.price,
                store_name=store_name,
            )
            if draft is not None:
                await self._notifications.create_and_dispatch(draft)

        self._session.add(
            ProductPriceHistory(
                product_variant_id=variant.id,
                store_name=store_name,
                price=item.price,
                quantity=item.qty,
                unit=unit,
                purchased_at=purchased_at or datetime.now(UTC),
                receipt_item_id=item.id,
                user_id=user_id,
            )
        )
        await self._session.flush()
        return variant

    async def _last_price(self, variant_id: UUID, *, user_id: UUID) -> Decimal | None:
        result = await self._session.execute(
            select(ProductPriceHistory.price)
            .where(
                ProductPriceHistory.product_variant_id == variant_id,
                ProductPriceHistory.user_id == user_id,
                ProductPriceHistory.price.is_not(None),
            )
            .order_by(ProductPriceHistory.purchased_at.desc())
            .limit(1)
        )
        value = result.scalar_one_or_none()
        return Decimal(str(value)) if value is not None else None

    async def _find_or_create_product(
        self, brand: str | None, name: str, category_id: UUID | None
    ) -> Product:
        q = select(Product).where(Product.name == name)
        if brand:
            q = q.where(Product.brand == brand)
        else:
            q = q.where(Product.brand.is_(None))
        result = await self._session.execute(q)
        product = result.scalar_one_or_none()
        if product is None:
            product = Product(brand=brand, name=name, category_id=category_id)
            self._session.add(product)
            await self._session.flush()
        elif category_id and product.category_id is None:
            product.category_id = category_id
        return product

    async def _find_or_create_variant(
        self,
        product_id: UUID,
        weight: Decimal | None,
        volume: Decimal | None,
        unit: str,
    ) -> ProductVariant:
        result = await self._session.execute(
            select(ProductVariant).where(
                ProductVariant.product_id == product_id,
                ProductVariant.weight == weight,
                ProductVariant.volume == volume,
                ProductVariant.unit == unit,
            )
        )
        variant = result.scalar_one_or_none()
        if variant is None:
            variant = ProductVariant(
                product_id=product_id,
                weight=weight,
                volume=volume,
                unit=unit,
            )
            self._session.add(variant)
            await self._session.flush()
        return variant

    @staticmethod
    def _parse_name(raw: str) -> tuple[str | None, str, Decimal | None, Decimal | None, str]:
        text = " ".join(raw.strip().split())
        weight = volume = None
        unit = "pcs"
        match = _VOLUME_RE.search(text)
        if match:
            num = Decimal(match.group("num").replace(",", "."))
            u = match.group("unit").lower()
            if u in {"мл", "ml"}:
                volume, unit = num, "ml"
            elif u in {"л", "l"}:
                volume, unit = num * 1000, "ml"
            elif u in {"г", "g"}:
                weight, unit = num, "g"
            elif u in {"кг", "kg"}:
                weight, unit = num * 1000, "g"
            text = (text[: match.start()] + text[match.end() :]).strip()

        brand = None
        parts = text.split(" ", 1)
        known_brands = {"простоквашино", "домик", "валентина", "coca-cola", "pepsi"}
        if parts and parts[0].lower() in known_brands:
            brand = parts[0]
            text = parts[1] if len(parts) > 1 else parts[0]
        return brand, text or raw.strip(), weight, volume, unit
