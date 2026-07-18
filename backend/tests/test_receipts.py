from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "receipts@berrio.app") -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "display_name": "Receipt User",
            "device_id": "receipt-device-001",
            "device_name": "pytest",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_scan_receipt_creates_items(client: AsyncClient) -> None:
    tokens = await _register(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    scan = await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={
            "fn": "9281000100123456",
            "fd": "12345",
            "fp": "987654321",
            "total_amount": "250.00",
        },
    )
    assert scan.status_code == 201, scan.text
    body = scan.json()
    assert body["status"] == "done"
    assert body["store_name"] == "Пятёрочка"
    assert len(body["items"]) == 2
    assert Decimal(str(body["total_amount"])) == Decimal("250.00")


@pytest.mark.asyncio
async def test_scan_is_idempotent(client: AsyncClient) -> None:
    tokens = await _register(client, email="idem@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    payload = {"fn": "111", "fd": "222", "fp": "333", "total_amount": "100.00"}

    first = await client.post("/api/v1/receipts/scan", headers=headers, json=payload)
    second = await client.post("/api/v1/receipts/scan", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_list_and_get_receipt(client: AsyncClient) -> None:
    tokens = await _register(client, email="list@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    created = await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "a", "fd": "b", "fp": "c", "total_amount": "10.00"},
    )
    receipt_id = created.json()["id"]

    listed = await client.get("/api/v1/receipts", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    got = await client.get(f"/api/v1/receipts/{receipt_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["fn"] == "a"


@pytest.mark.asyncio
async def test_scan_requires_auth(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/receipts/scan",
        json={"fn": "1", "fd": "2", "fp": "3"},
    )
    assert res.status_code == 401
