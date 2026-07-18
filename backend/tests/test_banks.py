import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_bank_parse_email(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bank@berrio.app",
            "password": "Secret123!",
            "display_name": "B",
            "device_id": "bank-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    conn = await client.post(
        "/api/v1/banks/connections",
        headers=headers,
        json={"bank_code": "tinkoff", "label": "T main"},
    )
    assert conn.status_code == 201

    parsed = await client.post(
        "/api/v1/banks/parse-email",
        headers=headers,
        json={
            "bank_code": "tinkoff",
            "subject": "Операция по карте",
            "body": "Покупка Пятёрочка 1 250,50 RUB",
        },
    )
    assert parsed.status_code == 200, parsed.text
    assert len(parsed.json()) == 1
    assert parsed.json()[0]["merchant_raw"] == "Пятёрочка"

    txs = await client.get("/api/v1/banks/transactions", headers=headers)
    assert txs.status_code == 200
    assert len(txs.json()) >= 1
