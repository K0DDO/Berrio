import pytest
from httpx import AsyncClient


async def _auth(client: AsyncClient) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "analytics@berrio.app",
            "password": "Secret123!",
            "display_name": "A",
            "device_id": "analytics-device",
        },
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_analytics_summary_after_receipt(client: AsyncClient) -> None:
    tokens = await _auth(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "an1", "fd": "an2", "fp": "an3", "total_amount": "250.00"},
    )
    summary = await client.get("/api/v1/analytics/summary?period=month", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["receipt_count"] >= 1
    assert float(body["total_spend"]) > 0
    assert body["berrio_score"] is not None
    assert 0 <= body["berrio_score"] <= 100
    assert "positive" in body["score_factors"]


@pytest.mark.asyncio
async def test_financial_health_score_endpoint(client: AsyncClient) -> None:
    tokens = await _auth(client)
    # re-register conflict — use unique via login path from previous? use new email
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "health@berrio.app",
            "password": "Secret123!",
            "display_name": "H",
            "device_id": "health-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    score = await client.get("/api/v1/financial-health/score", headers=headers)
    assert score.status_code == 200
    assert "score" in score.json()
