import pytest
from httpx import AsyncClient


async def _reg(client: AsyncClient, email: str, device: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "display_name": email.split("@")[0],
            "device_id": device,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_family_invite_accept_flow(client: AsyncClient) -> None:
    owner = await _reg(client, "owner-inv@berrio.app", "owner-inv-device")
    guest = await _reg(client, "guest-inv@berrio.app", "guest-inv-device")
    owner_h = {"Authorization": f"Bearer {owner['access_token']}"}
    guest_h = {"Authorization": f"Bearer {guest['access_token']}"}

    family = await client.post(
        "/api/v1/families",
        headers=owner_h,
        json={"name": "Invite Family"},
    )
    assert family.status_code == 201
    family_id = family.json()["id"]

    invite = await client.post(
        f"/api/v1/families/{family_id}/invites",
        headers=owner_h,
        json={"role": "PARENT", "email": "guest-inv@berrio.app"},
    )
    assert invite.status_code == 201, invite.text
    body = invite.json()
    assert body["token"]
    assert body["has_email_lock"] is True
    token = body["token"]

    listed = await client.get(f"/api/v1/families/{family_id}/invites", headers=owner_h)
    assert listed.status_code == 200
    assert listed.json()[0]["token"] is None

    # Wrong account cannot accept email-locked invite
    stranger = await _reg(client, "stranger@berrio.app", "stranger-device")
    stranger_h = {"Authorization": f"Bearer {stranger['access_token']}"}
    bad = await client.post(
        "/api/v1/families/invites/accept",
        headers=stranger_h,
        json={"token": token},
    )
    assert bad.status_code == 403

    ok = await client.post(
        "/api/v1/families/invites/accept",
        headers=guest_h,
        json={"token": token},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["role"] == "PARENT"

    members = await client.get(f"/api/v1/families/{family_id}/members", headers=owner_h)
    assert members.status_code == 200
    assert len(members.json()) == 2

    # Token cannot be reused
    again = await client.post(
        "/api/v1/families/invites/accept",
        headers=guest_h,
        json={"token": token},
    )
    assert again.status_code in {400, 409}


@pytest.mark.asyncio
async def test_family_invite_revoke(client: AsyncClient) -> None:
    owner = await _reg(client, "owner-rev@berrio.app", "owner-rev-device")
    owner_h = {"Authorization": f"Bearer {owner['access_token']}"}
    family = await client.post(
        "/api/v1/families",
        headers=owner_h,
        json={"name": "Revoke Family"},
    )
    family_id = family.json()["id"]
    invite = await client.post(
        f"/api/v1/families/{family_id}/invites",
        headers=owner_h,
        json={"role": "CHILD"},
    )
    assert invite.status_code == 201
    invite_id = invite.json()["id"]
    token = invite.json()["token"]

    revoked = await client.delete(
        f"/api/v1/families/{family_id}/invites/{invite_id}",
        headers=owner_h,
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"

    guest = await _reg(client, "guest-rev@berrio.app", "guest-rev-device")
    guest_h = {"Authorization": f"Bearer {guest['access_token']}"}
    accept = await client.post(
        "/api/v1/families/invites/accept",
        headers=guest_h,
        json={"token": token},
    )
    assert accept.status_code == 400


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
