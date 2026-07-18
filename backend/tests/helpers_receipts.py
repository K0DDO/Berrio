"""Helpers for receipt API tests — stub FNS never invents merchants/items."""

from __future__ import annotations

from decimal import Decimal

from httpx import AsyncClient


async def confirm_grocery_receipt(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    fn: str,
    fd: str,
    fp: str,
    total: str = "250.00",
    purchased_at: str | None = None,
) -> dict:
    """Scan QR → needs_confirmation → user confirms grocery lines."""
    payload: dict = {"fn": fn, "fd": fd, "fp": fp, "total_amount": total}
    if purchased_at:
        payload["purchased_at"] = purchased_at
    scan = await client.post("/api/v1/receipts/scan", headers=headers, json=payload)
    assert scan.status_code == 201, scan.text
    body = scan.json()
    assert body["status"] == "needs_confirmation"
    assert body["requires_confirmation"] is True
    assert body["store_name"] is None
    assert body["items"] == []

    amount = Decimal(total)
    milk = (amount * Decimal("0.4")).quantize(Decimal("0.01"))
    bread = (amount - milk).quantize(Decimal("0.01"))
    confirm_payload: dict = {
        "store_name": "Пятёрочка",
        "total_amount": total,
        "items": [
            {
                "name": "Молоко Простоквашино 2.5%",
                "qty": "1",
                "price": str(milk),
                "sum": str(milk),
                "confidence": 1.0,
            },
            {
                "name": "Хлеб Бородинский",
                "qty": "1",
                "price": str(bread),
                "sum": str(bread),
                "confidence": 1.0,
            },
        ],
    }
    if purchased_at:
        confirm_payload["purchased_at"] = purchased_at
    confirmed = await client.patch(
        f"/api/v1/receipts/{body['id']}/confirm",
        headers=headers,
        json=confirm_payload,
    )
    assert confirmed.status_code == 200, confirmed.text
    out = confirmed.json()
    assert out["status"] == "done"
    assert out["store_name"] == "Пятёрочка"
    assert len(out["items"]) == 2
    return out
