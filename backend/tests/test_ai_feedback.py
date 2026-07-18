import pytest
from httpx import AsyncClient
from tests.helpers_receipts import confirm_grocery_receipt


@pytest.mark.asyncio
async def test_ai_insight_feedback(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "feedback@berrio.app",
            "password": "Secret123!",
            "display_name": "FB",
            "device_id": "fb-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    await confirm_grocery_receipt(client, headers, fn="fb1", fd="fb2", fp="fb3", total="150.00")
    insights = await client.get("/api/v1/ai/insights", headers=headers)
    assert insights.status_code == 200
    items = insights.json()
    assert items
    insight_id = items[0]["id"]
    assert insight_id

    fb = await client.post(
        f"/api/v1/ai/insights/{insight_id}/feedback",
        headers=headers,
        json={"feedback_type": "HELPFUL"},
    )
    assert fb.status_code == 200, fb.text
    assert fb.json()["feedback_type"] == "HELPFUL"
    assert fb.json()["rating"] == 1

    again = await client.post(
        f"/api/v1/ai/insights/{insight_id}/feedback",
        headers=headers,
        json={"feedback_type": "NOT_HELPFUL"},
    )
    assert again.status_code == 200
    assert again.json()["feedback_type"] == "NOT_HELPFUL"
    assert again.json()["rating"] == -1
