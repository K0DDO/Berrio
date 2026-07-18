"""Receipt ↔ bank reconciliation."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.banks.models import Transaction
from app.modules.receipts.models import Receipt, ReceiptStatus
from app.modules.reconciliation.engine import ReconciliationEngine


@pytest.mark.asyncio
async def test_engine_scores_exact_amount_and_merchant() -> None:
    engine = ReconciliationEngine()
    now = datetime.now(UTC)
    receipt = Receipt(
        id=uuid4(),
        user_id=uuid4(),
        fn="1",
        fd="2",
        fp="3",
        purchased_at=now,
        total_amount=Decimal("1250.50"),
        store_name="Пятёрочка",
        status=ReceiptStatus.DONE,
    )
    tx = Transaction(
        id=uuid4(),
        user_id=receipt.user_id,
        amount=Decimal("1250.50"),
        currency="RUB",
        merchant_raw="Пятёрочка",
        booked_at=now,
        external_id="ext-1",
    )
    candidate = await engine.score_pair(receipt, tx)
    assert candidate is not None
    assert candidate.score >= Decimal("80")
    assert candidate.reasons["amount"] == "exact"
    assert candidate.confidence > 0


@pytest.mark.asyncio
async def test_reconciliation_run_confirm(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "recon@berrio.app",
            "password": "Secret123!",
            "display_name": "R",
            "device_id": "recon-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    receipt = await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={
            "fn": "r1",
            "fd": "r2",
            "fp": "r3",
            "total_amount": "1250.50",
            "purchased_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    assert receipt.status_code == 201, receipt.text

    await client.post(
        "/api/v1/banks/connections",
        headers=headers,
        json={"bank_code": "tinkoff", "label": "T"},
    )
    parsed = await client.post(
        "/api/v1/banks/parse-email",
        headers=headers,
        json={
            "bank_code": "tinkoff",
            "subject": "Операция",
            "body": "Покупка Пятёрочка 1 250,50 RUB",
        },
    )
    assert parsed.status_code == 200, parsed.text

    run = await client.post("/api/v1/reconciliation/run", headers=headers)
    assert run.status_code == 200, run.text
    body = run.json()
    assert "created" in body
    assert "suggestions" in body

    for status in ("SUGGESTED", "MATCHED", "CONFLICT"):
        suggestions = await client.get(
            f"/api/v1/reconciliation/suggestions?status={status}",
            headers=headers,
        )
        assert suggestions.status_code == 200
        if suggestions.json():
            mid = suggestions.json()[0]["id"]
            confirmed = await client.post(
                f"/api/v1/reconciliation/{mid}/confirm",
                headers=headers,
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["status"] == "MATCHED"
            break
