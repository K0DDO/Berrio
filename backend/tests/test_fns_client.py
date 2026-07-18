"""Real FNS client parsing + factory fallback."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.fns_client import (
    ProverkaChekaFnsClient,
    StubFnsClient,
    get_fns_client,
)


@pytest.mark.asyncio
async def test_stub_client_deterministic() -> None:
    client = StubFnsClient()
    data = await client.fetch(fn="1", fd="2", fp="3", total_amount=Decimal("100.00"))
    assert data.store_name == "Пятёрочка"
    assert data.total_amount == Decimal("100.00")
    assert len(data.items) == 2


@pytest.mark.asyncio
async def test_proverkacheka_parses_json_payload() -> None:
    client = ProverkaChekaFnsClient(token="test-token")
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "code": 1,
        "data": {
            "json": {
                "user": "ООО Ромашка",
                "userInn": "7701234567",
                "totalSum": 25000,
                "dateTime": "2026-07-10T12:30:00",
                "items": [
                    {"name": "Молоко", "price": 10000, "quantity": 1, "sum": 10000},
                    {"name": "Хлеб", "price": 15000, "quantity": 1, "sum": 15000},
                ],
            }
        },
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=fake_response)

    with patch("app.integrations.fns_client.httpx.AsyncClient", return_value=mock_client):
        data = await client.fetch(
            fn="9281",
            fd="123",
            fp="456",
            purchased_at=datetime(2026, 7, 10, 12, 30, tzinfo=UTC),
            total_amount=Decimal("250.00"),
        )

    assert data.store_name == "ООО Ромашка"
    assert data.store_inn == "7701234567"
    assert data.total_amount == Decimal("250.00")
    assert data.items[0].price == Decimal("100.00")
    assert len(data.items) == 2
    mock_client.post.assert_awaited()


def test_factory_uses_stub_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.delenv("FNS_API_TOKEN", raising=False)
    monkeypatch.setenv("FNS_PROVIDER", "auto")
    get_settings.cache_clear()
    client = get_fns_client()
    assert isinstance(client, StubFnsClient)
    get_settings.cache_clear()
