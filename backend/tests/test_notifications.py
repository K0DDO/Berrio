"""Smart notifications — rules engine + API persistence."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.notifications.models import NotificationSeverity, NotificationType
from app.modules.notifications.rules import NotificationRulesEngine
from tests.helpers_receipts import confirm_grocery_receipt


async def _auth(client: AsyncClient, email: str) -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "display_name": "Notify",
            "device_id": f"dev-{email}",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_budget_rules_80_and_100() -> None:
    engine = NotificationRulesEngine()
    uid = uuid4()
    bid = uuid4()
    warn = engine.budget_monitoring(
        user_id=uid,
        family_id=None,
        budget_id=bid,
        budget_name="Food",
        spent=Decimal("8000"),
        limit_amount=Decimal("10000"),
    )
    assert len(warn) == 1
    assert warn[0].type == NotificationType.BUDGET_WARNING
    assert warn[0].severity == NotificationSeverity.WARNING

    crit = engine.budget_monitoring(
        user_id=uid,
        family_id=None,
        budget_id=bid,
        budget_name="Food",
        spent=Decimal("10000"),
        limit_amount=Decimal("10000"),
    )
    assert len(crit) == 1
    assert crit[0].type == NotificationType.BUDGET_EXCEEDED
    assert crit[0].severity == NotificationSeverity.CRITICAL


def test_price_change_rule() -> None:
    engine = NotificationRulesEngine()
    draft = engine.price_change(
        user_id=uuid4(),
        product_name="Молоко",
        variant_id=uuid4(),
        old_price=Decimal("100"),
        new_price=Decimal("130"),
    )
    assert draft is not None
    assert draft.type == NotificationType.PRICE_CHANGE
    assert "30%" in draft.message


def test_goal_remaining_20() -> None:
    engine = NotificationRulesEngine()
    draft = engine.goal_progress(
        user_id=uuid4(),
        family_id=None,
        goal_id=uuid4(),
        goal_name="Vacation",
        current=Decimal("80000"),
        target=Decimal("100000"),
    )
    assert draft is not None
    assert "20%" in draft.message


def test_unusual_spending_rule() -> None:
    engine = NotificationRulesEngine()
    draft = engine.unusual_spending(
        user_id=uuid4(),
        receipt_id=uuid4(),
        amount=Decimal("5000"),
        average=Decimal("1000"),
        store_name="Пятёрочка",
    )
    assert draft is not None
    assert draft.title == "Unusual purchase"


@pytest.mark.asyncio
async def test_notifications_api_list_and_read(client: AsyncClient) -> None:
    tokens = await _auth(client, "notify-api@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Create a goal near completion → GOAL_PROGRESS notification
    goal = await client.post(
        "/api/v1/goals",
        headers=headers,
        json={"name": "Trip", "target_amount": "1000.00", "current_amount": "0"},
    )
    assert goal.status_code == 201
    goal_id = goal.json()["id"]
    progressed = await client.post(
        f"/api/v1/goals/{goal_id}/progress",
        headers=headers,
        json={"current_amount": "850.00"},
    )
    assert progressed.status_code == 200

    listed = await client.get("/api/v1/notifications", headers=headers)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) >= 1
    assert items[0]["type"] == "GOAL_PROGRESS"
    assert items[0]["read_at"] is None
    assert "explanation" in items[0]["payload"]

    nid = items[0]["id"]
    marked = await client.post(f"/api/v1/notifications/{nid}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None


@pytest.mark.asyncio
async def test_budget_check_creates_warning_notification(client: AsyncClient) -> None:
    tokens = await _auth(client, "notify-budget@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Seed spend via confirmed receipt (stub never invents items)
    await confirm_grocery_receipt(
        client,
        headers,
        fn="nb1",
        fd="nb2",
        fp="nb3",
        total="9000.00",
        purchased_at="2026-07-10T12:00:00Z",
    )

    budget = await client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "name": "July",
            "limit_amount": "10000.00",
            "period_type": "MONTH",
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
        },
    )
    assert budget.status_code == 201
    checked = await client.post(
        f"/api/v1/budgets/{budget.json()['id']}/check",
        headers=headers,
    )
    assert checked.status_code == 200

    notes = await client.get("/api/v1/notifications", headers=headers)
    types = {n["type"] for n in notes.json()}
    assert "BUDGET_WARNING" in types or "BUDGET_EXCEEDED" in types or "UNUSUAL_SPENDING" in types
