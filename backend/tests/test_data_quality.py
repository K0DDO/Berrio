"""Data quality suite — categorization, merchants, products, prices, reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.fixtures.beta_dataset import (
    CATEGORIZATION_MIN_ACCURACY,
    LINE_ITEMS,
    STORES,
    TRANSACTIONS,
)
from tests.helpers_receipts import confirm_grocery_receipt

from app.modules.banks.models import Transaction
from app.modules.categorization.engine import (
    CategorizationRequest,
    RuleBasedCategorizationEngine,
    seed_default_categories,
)
from app.modules.merchants.normalizer import MerchantNormalizer
from app.modules.products.service import ProductService
from app.modules.receipts.models import Receipt, ReceiptItem, ReceiptStatus
from app.modules.reconciliation.engine import ReconciliationEngine


@pytest.mark.asyncio
async def test_merchant_normalization_fixtures() -> None:
    normalizer = MerchantNormalizer()
    for store in STORES:
        for raw in store.raw_names:
            result = await normalizer.normalize(raw)
            assert result.canonical_name == store.canonical, f"{raw=} → {result.canonical_name}"


@pytest.mark.asyncio
async def test_categorization_accuracy(db_engine) -> None:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        slugs = await seed_default_categories(session)
        await session.commit()
        engine = RuleBasedCategorizationEngine(session)
        hits = 0
        for item in LINE_ITEMS:
            result = await engine.categorize(CategorizationRequest(name_raw=item.name_raw))
            if result.category_id is None:
                continue
            slug = next(s for s, cid in slugs.items() if cid == result.category_id)
            if item.expected_slug_contains in slug or slug == item.expected_slug_contains:
                hits += 1
        accuracy = hits / len(LINE_ITEMS)
        assert accuracy >= CATEGORIZATION_MIN_ACCURACY, f"accuracy={accuracy:.2f} hits={hits}"


@pytest.mark.asyncio
async def test_product_normalization_and_price_history(db_engine) -> None:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await seed_default_categories(session)
        await session.commit()
        svc = ProductService(session)
        user_id = uuid4()
        receipt = Receipt(
            id=uuid4(),
            user_id=user_id,
            fn="dq1",
            fd="dq2",
            fp="dq3",
            purchased_at=datetime.now(UTC) - timedelta(days=7),
            total_amount=Decimal("100"),
            store_name="Пятёрочка",
            status=ReceiptStatus.DONE,
        )
        session.add(receipt)
        await session.flush()

        fixture = LINE_ITEMS[0]
        item1 = ReceiptItem(
            receipt_id=receipt.id,
            name_raw=fixture.name_raw,
            qty=Decimal("1"),
            price=Decimal("80.00"),
            sum=Decimal("80.00"),
        )
        session.add(item1)
        await session.flush()
        brand, _name, _w, volume, unit = ProductService._parse_name(fixture.name_raw)
        assert brand is not None
        assert brand.lower() == (fixture.expect_brand or "").lower()
        assert volume == fixture.expect_volume_ml
        assert unit == "ml"

        v1 = await svc.resolve_for_receipt_item(
            item1,
            user_id=user_id,
            store_name="Пятёрочка",
            purchased_at=receipt.purchased_at,
            category_id=None,
        )
        await session.flush()

        receipt2 = Receipt(
            id=uuid4(),
            user_id=user_id,
            fn="dq4",
            fd="dq5",
            fp="dq6",
            purchased_at=datetime.now(UTC),
            total_amount=Decimal("110"),
            store_name="Пятёрочка",
            status=ReceiptStatus.DONE,
        )
        session.add(receipt2)
        await session.flush()
        item2 = ReceiptItem(
            receipt_id=receipt2.id,
            name_raw=fixture.name_raw,
            qty=Decimal("1"),
            price=Decimal("89.00"),
            sum=Decimal("89.00"),
        )
        session.add(item2)
        await session.flush()
        v2 = await svc.resolve_for_receipt_item(
            item2,
            user_id=user_id,
            store_name="Пятёрочка",
            purchased_at=receipt2.purchased_at,
            category_id=None,
        )
        await session.commit()
        assert v1.id == v2.id
        prev = await svc._last_price(v2.id, user_id=user_id)
        assert prev == Decimal("89.00")


@pytest.mark.asyncio
async def test_reconciliation_confidence_on_fixtures() -> None:
    engine = ReconciliationEngine()
    now = datetime.now(UTC)
    user_id = uuid4()
    receipt = Receipt(
        id=uuid4(),
        user_id=user_id,
        fn="1",
        fd="2",
        fp="3",
        purchased_at=now,
        total_amount=TRANSACTIONS[0].amount,
        store_name="Пятёрочка",
        status=ReceiptStatus.DONE,
    )
    scores: list[Decimal] = []
    for tx_fix in TRANSACTIONS[:2]:
        tx = Transaction(
            id=uuid4(),
            user_id=user_id,
            amount=tx_fix.amount,
            currency="RUB",
            merchant_raw=tx_fix.merchant_raw,
            booked_at=now,
            external_id=str(uuid4()),
        )
        candidate = await engine.score_pair(receipt, tx)
        assert candidate is not None, tx_fix.note
        assert candidate.confidence > 0
        scores.append(candidate.confidence)
    assert scores[0] >= Decimal("50")


@pytest.mark.asyncio
async def test_api_seed_scan_categorizes_stub_items(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dq-api@berrio.app",
            "password": "Secret123!",
            "display_name": "DQ",
            "device_id": "dq-api-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    body = await confirm_grocery_receipt(
        client, headers, fn="dqapi1", fd="dqapi2", fp="dqapi3", total="250.00"
    )
    items = body["items"]
    assert all(i.get("category_id") for i in items)
    assert all(i.get("product_variant_id") for i in items)

    service_hits = 0
    for item in LINE_ITEMS:
        preview = await client.post(
            "/api/v1/categories/preview",
            headers=headers,
            json={"name_raw": item.name_raw},
        )
        assert preview.status_code == 200
        body = preview.json()
        if body.get("category_id") and body.get("source") in {"rules", "user_rule"}:
            service_hits += 1
    assert service_hits / len(LINE_ITEMS) >= CATEGORIZATION_MIN_ACCURACY
