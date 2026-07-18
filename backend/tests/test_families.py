import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_family_create_and_permissions(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "family@berrio.app",
            "password": "Secret123!",
            "display_name": "Parent",
            "device_id": "family-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    created = await client.post(
        "/api/v1/families",
        headers=headers,
        json={"name": "Семья Беррио"},
    )
    assert created.status_code == 201, created.text
    family_id = created.json()["id"]

    members = await client.get(f"/api/v1/families/{family_id}/members", headers=headers)
    assert members.status_code == 200
    assert len(members.json()) == 1
    owner = members.json()[0]
    assert owner["role"] == "OWNER"
    assert owner["permissions"]["can_view_family_budget"] is True

    patched = await client.patch(
        f"/api/v1/families/{family_id}/members/{owner['id']}/permissions",
        headers=headers,
        json={"permission_key": "can_receive_reports", "allowed": False},
    )
    assert patched.status_code == 200
    assert patched.json()["permissions"]["can_receive_reports"] is False
