import pytest
from httpx import AsyncClient


async def _auth(client: AsyncClient, email: str) -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "display_name": "Goals User",
            "device_id": f"device-{email}",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_goals_crud_and_progress(client: AsyncClient) -> None:
    tokens = await _auth(client, "goals@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    created = await client.post(
        "/api/v1/goals",
        headers=headers,
        json={
            "name": "Emergency fund",
            "target_amount": "100000.00",
            "current_amount": "10000.00",
        },
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    assert created.json()["progress_pct"] == 10.0

    listed = await client.get("/api/v1/goals", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    progressed = await client.post(
        f"/api/v1/goals/{goal_id}/progress",
        headers=headers,
        json={"current_amount": "100000.00"},
    )
    assert progressed.status_code == 200
    assert progressed.json()["status"] == "COMPLETED"
    assert progressed.json()["progress_pct"] == 100.0


@pytest.mark.asyncio
async def test_budgets_create_and_spend_check(client: AsyncClient) -> None:
    tokens = await _auth(client, "budgets@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    created = await client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "name": "Food",
            "limit_amount": "5000.00",
            "period_type": "MONTH",
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
        },
    )
    assert created.status_code == 201, created.text
    budget = created.json()
    assert budget["spent_amount"] == "0.00"
    assert budget["over_budget"] is False

    listed = await client.get("/api/v1/budgets", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    checked = await client.post(
        f"/api/v1/budgets/{budget['id']}/check",
        headers=headers,
    )
    assert checked.status_code == 200
