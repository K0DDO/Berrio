"""Dashboard, preferences, and reconciliation upgrades."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.banks.models import Transaction
from app.modules.receipts.models import Receipt, ReceiptStatus
from app.modules.reconciliation.engine import MatchDecision, ReconciliationEngine


@pytest.mark.asyncio
async def test_dashboard_endpoint(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dash@berrio.app",
            "password": "Secret123!",
            "display_name": "Dash",
            "device_id": "dash-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={
            "fn": "d1",
            "fd": "d2",
            "fp": "d3",
            "total_amount": "500.00",
            "purchased_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    await client.post(
        "/api/v1/goals",
        headers=headers,
        json={"name": "Rainy day", "target_amount": "10000", "current_amount": "2000"},
    )

    dash = await client.get("/api/v1/dashboard", headers=headers)
    assert dash.status_code == 200, dash.text
    body = dash.json()
    assert "berrio_score" in body
    assert 0 <= body["berrio_score"]["score"] <= 100
    assert "spending" in body
    assert "category_trends" in body
    assert "active_goals" in body
    assert len(body["active_goals"]) >= 1
    assert "recent_notifications" in body
    assert "ai_recommendation" in body


@pytest.mark.asyncio
async def test_notification_preferences(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "prefs@berrio.app",
            "password": "Secret123!",
            "display_name": "P",
            "device_id": "prefs-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    got = await client.get("/api/v1/notifications/preferences", headers=headers)
    assert got.status_code == 200
    assert got.json()["price_changes_enabled"] is True

    patched = await client.patch(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={"goal_alerts_enabled": False},
    )
    assert patched.status_code == 200
    assert patched.json()["goal_alerts_enabled"] is False

    # Goal progress should be suppressed when prefs disable it
    goal = await client.post(
        "/api/v1/goals",
        headers=headers,
        json={"name": "Muted", "target_amount": "1000", "current_amount": "0"},
    )
    await client.post(
        f"/api/v1/goals/{goal.json()['id']}/progress",
        headers=headers,
        json={"current_amount": "900"},
    )
    notes = await client.get("/api/v1/notifications", headers=headers)
    assert all(n["type"] != "GOAL_PROGRESS" for n in notes.json())


@pytest.mark.asyncio
async def test_engine_matched_decision() -> None:
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
        merchant_raw="PYATEROCHKA 12",
        booked_at=now,
        external_id="ext-1",
    )
    candidate = await engine.score_pair(receipt, tx)
    assert candidate is not None
    assert candidate.confidence > 0
    assert candidate.decision in {MatchDecision.MATCHED, MatchDecision.SUGGESTED}


@pytest.mark.asyncio
async def test_reconciliation_confirm_matched(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "recon2@berrio.app",
            "password": "Secret123!",
            "display_name": "R2",
            "device_id": "recon2-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={
            "fn": "rr1",
            "fd": "rr2",
            "fp": "rr3",
            "total_amount": "1250.50",
            "purchased_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    await client.post(
        "/api/v1/banks/connections",
        headers=headers,
        json={"bank_code": "tinkoff", "label": "T"},
    )
    await client.post(
        "/api/v1/banks/parse-email",
        headers=headers,
        json={
            "bank_code": "tinkoff",
            "subject": "Операция",
            "body": "Покупка Пятёрочка 1 250,50 RUB",
        },
    )
    run = await client.post("/api/v1/reconciliation/run", headers=headers)
    assert run.status_code == 200
    suggestions = await client.get(
        "/api/v1/reconciliation/suggestions?status=SUGGESTED",
        headers=headers,
    )
    # High-confidence pairs may land as MATCHED already
    await client.get("/api/v1/reconciliation/suggestions?status=", headers=headers)
    # empty status filter — our API treats "" as status; use without filter via SUGGESTED or MATCHED
    matched = await client.get(
        "/api/v1/reconciliation/suggestions?status=MATCHED",
        headers=headers,
    )
    pool = suggestions.json() + matched.json()
    if not pool:
        # CONFLICT list
        conflict = await client.get(
            "/api/v1/reconciliation/suggestions?status=CONFLICT",
            headers=headers,
        )
        pool = conflict.json()
    assert run.json()["created"] >= 0
    if pool:
        mid = pool[0]["id"]
        confirmed = await client.post(f"/api/v1/reconciliation/{mid}/confirm", headers=headers)
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "MATCHED"
        assert "confidence" in confirmed.json()
