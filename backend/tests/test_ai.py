import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_chat_and_insights(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ai@berrio.app",
            "password": "Secret123!",
            "display_name": "AI",
            "device_id": "ai-device-001",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    await client.post(
        "/api/v1/receipts/scan",
        headers=headers,
        json={"fn": "ai1", "fd": "ai2", "fp": "ai3", "total_amount": "120.00"},
    )

    chat = await client.post(
        "/api/v1/ai/chat",
        headers=headers,
        json={"message": "Можно ли купить ноутбук?", "period": "month"},
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["provider"] == "stub"
    assert "ноутбук" in body["reply"].lower() or "накоп" in body["reply"].lower()

    insights = await client.get("/api/v1/ai/insights", headers=headers)
    assert insights.status_code == 200
    payload = insights.json()
    assert len(payload) >= 1
    kinds = {i["kind"] for i in payload}
    assert "first_insight" in kinds or "onboarding" in kinds or "spend_focus" in kinds
    first = next((i for i in payload if i["kind"] == "first_insight"), None)
    if first:
        assert "расходы" in first["body"].lower() or "₽" in first["body"]
