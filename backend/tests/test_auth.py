import pytest
from httpx import AsyncClient

from app.core.encryption import EncryptionService, get_encryption_service
from app.core.security import (
    decrypt_email,
    encrypt_email,
    hash_email,
    hash_password,
    verify_password,
)


def test_argon2id_hash_and_verify() -> None:
    hashed = hash_password("Secret123!")
    assert hashed.startswith("$argon2id$")
    assert verify_password("Secret123!", hashed)
    assert not verify_password("wrong", hashed)


def test_aes_gcm_encryption_roundtrip() -> None:
    get_encryption_service.cache_clear()
    svc = EncryptionService.from_settings()
    blob = svc.encrypt_str("user@berrio.app")
    assert blob[0:1] == b"\x01"
    assert svc.decrypt_str(blob) == "user@berrio.app"
    # Different nonce each time
    assert svc.encrypt_str("user@berrio.app") != blob


def test_email_hash_normalized_unique_lookup() -> None:
    assert hash_email("  User@Berrio.APP ") == hash_email("user@berrio.app")
    assert hash_email("a@b.c") != hash_email("c@b.a")


def test_encrypt_email_uses_aes_gcm() -> None:
    get_encryption_service.cache_clear()
    blob = encrypt_email("  Alice@Berrio.APP ")
    assert decrypt_email(blob) == "alice@berrio.app"


@pytest.mark.asyncio
async def test_register_login_me_flow(client: AsyncClient, device_payload: dict) -> None:
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@berrio.app",
            "password": "Secret123!",
            "display_name": "Dima",
            **device_payload,
        },
    )
    assert register.status_code == 201, register.text
    body = register.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "user@berrio.app"
    assert body["user"]["email_verified"] is False

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["display_name"] == "Dima"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@berrio.app", "password": "Secret123!", **device_payload},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


@pytest.mark.asyncio
async def test_duplicate_register_conflict(client: AsyncClient, device_payload: dict) -> None:
    payload = {
        "email": "dup@berrio.app",
        "password": "Secret123!",
        "display_name": "A",
        **device_payload,
    }
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    again = await client.post("/api/v1/auth/register", json=payload)
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_detection(
    client: AsyncClient, device_payload: dict
) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotate@berrio.app",
            "password": "Secret123!",
            "display_name": "R",
            **device_payload,
        },
    )
    old_refresh = reg.json()["refresh_token"]

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh, "device_id": device_payload["device_id"]},
    )
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh, "device_id": device_payload["device_id"]},
    )
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_device_mismatch_on_refresh(client: AsyncClient, device_payload: dict) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "device@berrio.app",
            "password": "Secret123!",
            "display_name": "D",
            **device_payload,
        },
    )
    bad = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": reg.json()["refresh_token"], "device_id": "other-device-999"},
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient, device_payload: dict) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@berrio.app",
            "password": "Secret123!",
            "display_name": "L",
            **device_payload,
        },
    )
    refresh = reg.json()["refresh_token"]
    access = reg.json()["access_token"]

    out = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh, "device_id": device_payload["device_id"]},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert out.status_code == 200

    again = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh, "device_id": device_payload["device_id"]},
    )
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_revoke_all_sessions(client: AsyncClient, device_payload: dict) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "revoke@berrio.app",
            "password": "Secret123!",
            "display_name": "V",
            **device_payload,
        },
    )
    access = reg.json()["access_token"]
    refresh = reg.json()["refresh_token"]

    revoked = await client.post(
        "/api/v1/auth/revoke-all",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert revoked.status_code == 200

    again = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh, "device_id": device_payload["device_id"]},
    )
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient, device_payload: dict) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify@berrio.app",
            "password": "Secret123!",
            "display_name": "E",
            **device_payload,
        },
    )
    access = reg.json()["access_token"]

    requested = await client.post(
        "/api/v1/auth/verify-email/request",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert requested.status_code == 200
    detail = requested.json().get("detail") or ""
    assert detail.startswith("dev_token=")
    token = detail.removeprefix("dev_token=")

    confirmed = await client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"token": token},
    )
    assert confirmed.status_code == 200

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert me.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient, device_payload: dict) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "reset@berrio.app",
            "password": "Secret123!",
            "display_name": "P",
            **device_payload,
        },
    )

    requested = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "reset@berrio.app"},
    )
    assert requested.status_code == 200
    detail = requested.json().get("detail") or ""
    assert detail.startswith("dev_token=")
    token = detail.removeprefix("dev_token=")

    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "NewSecret123!"},
    )
    assert confirmed.status_code == 200

    # One-time: reuse rejected
    reuse = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "AnotherSecret123!"},
    )
    assert reuse.status_code == 400

    bad_old = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@berrio.app", "password": "Secret123!", **device_payload},
    )
    assert bad_old.status_code == 401

    ok_new = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@berrio.app", "password": "NewSecret123!", **device_payload},
    )
    assert ok_new.status_code == 200


@pytest.mark.asyncio
async def test_logout_requires_bearer(client: AsyncClient, device_payload: dict) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout-bearer@berrio.app",
            "password": "Secret123!",
            "display_name": "L",
            **device_payload,
        },
    )
    refresh = reg.json()["refresh_token"]
    no_auth = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh, "device_id": device_payload["device_id"]},
    )
    assert no_auth.status_code == 401


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient, device_payload: dict) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@berrio.app", "password": "Secret123!", **device_payload},
    )
    assert res.status_code == 401
