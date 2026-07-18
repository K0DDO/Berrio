import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scan_creates_product_variants(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "products@berrio.app",
            "password": "Secret123!",
            "display_name": "P",
            "device_id": "prod-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    scan = await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "pv1", "fd": "pv2", "fp": "pv3", "total_amount": "100.00"},
    )
    assert scan.status_code == 201, scan.text
    items = scan.json()["items"]
    assert len(items) >= 1
    assert all(i.get("product_variant_id") is not None for i in items)


@pytest.mark.asyncio
async def test_ai_insights_persisted(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ai2@berrio.app",
            "password": "Secret123!",
            "display_name": "A",
            "device_id": "ai2-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "aix", "fd": "aiy", "fp": "aiz", "total_amount": "80.00"},
    )
    first = await client.get("/api/v1/ai/insights", headers=headers)
    assert first.status_code == 200
    assert len(first.json()) >= 1
    second = await client.get("/api/v1/ai/insights", headers=headers)
    assert second.status_code == 200
    assert len(second.json()) >= 1


@pytest.mark.asyncio
async def test_family_visible_user_ids(client: AsyncClient) -> None:
    parent = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent2@berrio.app",
            "password": "Secret123!",
            "display_name": "Parent",
            "device_id": "parent-device-2",
        },
    )
    headers = {"Authorization": f"Bearer {parent.json()['access_token']}"}
    family = await client.post(
        "/api/v1/families",
        headers=headers,
        json={"name": "Test Family"},
    )
    family_id = family.json()["id"]
    visible = await client.get(
        f"/api/v1/families/{family_id}/visible-user-ids",
        headers=headers,
    )
    assert visible.status_code == 200
    assert parent.json()["user"]["id"] in visible.json()


@pytest.mark.asyncio
async def test_health_score_uses_receipt_spend(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "health2@berrio.app",
            "password": "Secret123!",
            "display_name": "H",
            "device_id": "health2-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "h1", "fd": "h2", "fp": "h3", "total_amount": "200.00"},
    )
    score = await client.get("/api/v1/financial-health/score", headers=headers)
    assert score.status_code == 200
    body = score.json()
    assert body["score"] >= 70
    assert "есть данные о покупках" in body["factors"]["positive"]
