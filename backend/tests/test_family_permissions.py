"""Family permission checker must gate receipts/analytics/AI/transactions."""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, device: str, name: str = "U") -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "display_name": name,
            "device_id": device,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_family_permission_required_for_analytics(client: AsyncClient) -> None:
    parent = await _register(client, "perm-parent@berrio.app", "perm-parent-device", "Parent")
    parent_headers = {"Authorization": f"Bearer {parent['access_token']}"}
    family = await client.post(
        "/api/v1/families",
        headers=parent_headers,
        json={"name": "Perm Family"},
    )
    assert family.status_code == 201
    family_id = family.json()["id"]

    ok = await client.get("/api/v1/analytics/summary?period=month", headers=parent_headers)
    assert ok.status_code == 200

    fam_ok = await client.get(
        f"/api/v1/analytics/summary?period=month&family_id={family_id}",
        headers=parent_headers,
    )
    assert fam_ok.status_code == 200

    stranger = await _register(client, "perm-stranger@berrio.app", "perm-stranger-device")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}
    denied = await client.get(
        f"/api/v1/receipts?family_id={family_id}",
        headers=stranger_headers,
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_family_permission_gates_ai_and_transactions(client: AsyncClient) -> None:
    owner = await _register(client, "gate-owner@berrio.app", "gate-owner", "Owner")
    owner_h = {"Authorization": f"Bearer {owner['access_token']}"}
    family = await client.post("/api/v1/families", headers=owner_h, json={"name": "Gate"})
    family_id = family.json()["id"]

    outsider = await _register(client, "gate-out@berrio.app", "gate-out")
    out_h = {"Authorization": f"Bearer {outsider['access_token']}"}

    ai = await client.get(
        f"/api/v1/ai/insights?period=month&family_id={family_id}",
        headers=out_h,
    )
    assert ai.status_code == 403

    tx = await client.get(
        f"/api/v1/banks/transactions?family_id={family_id}",
        headers=out_h,
    )
    assert tx.status_code == 403

    # Owner may scope family domains
    ai_ok = await client.get(
        f"/api/v1/ai/insights?period=month&family_id={family_id}",
        headers=owner_h,
    )
    assert ai_ok.status_code == 200

    receipt = await client.get(
        f"/api/v1/receipts?family_id={family_id}",
        headers=owner_h,
    )
    assert receipt.status_code == 200
