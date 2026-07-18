"""Local beta launch — seed + env validation."""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.dev.seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_data


def test_blank_secret_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(
            secret_key="",
            email_hash_pepper="pepper",
            database_url="postgresql+asyncpg://berrio:berrio@localhost/berrio",
        )
    assert "SECRET_KEY" in str(exc.value)


@pytest.mark.asyncio
async def test_seed_demo_creates_user_and_receipts(client: AsyncClient, db_engine) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await seed_demo_data(session)
    assert result["email"] == DEMO_EMAIL
    assert result["receipts_processed"] >= 1
    assert result["insights"] >= 1

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "device_id": "seed-login-device",
        },
    )
    assert login.status_code == 200, login.text

    seed_api = await client.post("/api/v1/system/seed-demo")
    assert seed_api.status_code == 200
    assert seed_api.json()["email"] == DEMO_EMAIL
