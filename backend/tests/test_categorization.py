import pytest
from httpx import AsyncClient


async def _auth(client: AsyncClient, email: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "display_name": "Cat User",
            "device_id": "cat-device-001",
        },
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_receipt_items_get_categories(client: AsyncClient) -> None:
    tokens = await _auth(client, "cat1@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    scan = await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "c1", "fd": "c2", "fp": "c3", "total_amount": "100.00"},
    )
    assert scan.status_code == 201
    items = scan.json()["items"]
    assert len(items) == 2
    # Milk should map to dairy via system rule
    milk = next(i for i in items if "Молоко" in i["name_raw"])
    assert milk["category_id"] is not None


@pytest.mark.asyncio
async def test_preview_and_override_creates_user_rule(client: AsyncClient) -> None:
    tokens = await _auth(client, "cat2@berrio.app")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    cats = await client.get("/api/v1/categories", headers=headers)
    assert cats.status_code == 200
    categories = cats.json()
    cafe = next(c for c in categories if c["slug"] == "food.cafe")

    preview = await client.post(
        "/api/v1/categories/preview",
        headers=headers,
        json={"name_raw": "Молоко Простоквашино"},
    )
    assert preview.status_code == 200
    assert preview.json()["source"] in {"rules", "user_rule", "ai", "unknown"}

    scan = await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "x", "fd": "y", "fp": "z", "total_amount": "50.00"},
    )
    item_id = scan.json()["items"][0]["id"]

    override = await client.post(
        f"/api/v1/receipt-items/{item_id}/category",
        headers=headers,
        json={"category_id": cafe["id"], "create_rule": True},
    )
    assert override.status_code == 200
    assert override.json()["slug"] == "food.cafe"

    # New item with same name should follow user rule preference on next scan
    # (user rule pattern = full name_raw of first item)
