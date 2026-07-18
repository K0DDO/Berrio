"""Anti-hallucination receipt recognition pipeline tests."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.modules.receipts.recognition.pipeline import ReceiptRecognitionPipeline


@pytest.fixture
def pipeline() -> ReceiptRecognitionPipeline:
    return ReceiptRecognitionPipeline()


def test_dentistry_receipt_health_and_amount(pipeline: ReceiptRecognitionPipeline) -> None:
    text = "ООО Стоматология\n" "Услуга: лечение зуба\n" "Итого: 6500 руб\n"
    structured, validation = pipeline.analyze_text(text)
    assert structured.amount.value == Decimal("6500.00")
    assert structured.category_hint.value == "health"
    assert structured.merchant.value is not None
    assert "стоматолог" in structured.merchant.value.lower()
    assert "пятёр" not in (structured.merchant.value or "").lower()
    assert not any("молоко" in i.name.lower() for i in structured.items)
    assert not any("хлеб" in i.name.lower() for i in structured.items)


def test_dentistry_short_line(pipeline: ReceiptRecognitionPipeline) -> None:
    structured, _ = pipeline.analyze_text("лечение зуба 6500")
    assert structured.amount.value == Decimal("6500.00")
    assert structured.category_hint.value == "health"


def test_blurry_photo_requires_confirmation(pipeline: ReceiptRecognitionPipeline) -> None:
    structured, validation = pipeline.analyze_text("??? ## @@\nblur\n")
    assert structured.requires_confirmation is True
    assert validation.requires_confirmation is True
    assert structured.overall_confidence < 0.7


def test_grocery_receipt_food_category(pipeline: ReceiptRecognitionPipeline) -> None:
    text = "Пятёрочка\n" "Молоко 1 89.00\n" "Хлеб 1 45.00\n" "Итого: 134.00 руб\n"
    structured, _ = pipeline.analyze_text(text)
    assert structured.category_hint.value == "food"
    assert structured.amount.value == Decimal("134.00")
    assert structured.merchant.value is not None
    assert (
        "пятер" in structured.merchant.value.lower() or "пятёр" in structured.merchant.value.lower()
    )


def test_unreadable_does_not_auto_succeed(pipeline: ReceiptRecognitionPipeline) -> None:
    structured, validation = pipeline.analyze_text("   \n\t  ")
    assert structured.success is False
    assert structured.requires_confirmation is True
    assert validation.requires_confirmation is True
    assert structured.amount.value is None
    assert structured.items == []


def test_rejects_hallucinated_grocery_on_health_ocr(pipeline: ReceiptRecognitionPipeline) -> None:
    """If somehow grocery items appear with health OCR, validator flags it."""
    from app.modules.receipts.recognition.models import (
        ConfidenceField,
        RecognizedItem,
        StructuredReceipt,
    )
    from app.modules.receipts.recognition.validator import validate_structured

    fake = StructuredReceipt(
        merchant=ConfidenceField(value="Пятёрочка", confidence=0.9),
        amount=ConfidenceField(value=Decimal("6500"), confidence=0.9),
        items=[
            RecognizedItem(name="Молоко", sum=Decimal("2600"), confidence=0.9),
            RecognizedItem(name="Хлеб", sum=Decimal("3900"), confidence=0.9),
        ],
        category_hint=ConfidenceField(value="food", confidence=0.9),
        raw_ocr_text="ООО Стоматология\nлечение зуба\nИтого: 6500",
        overall_confidence=0.9,
        requires_confirmation=False,
        success=True,
    )
    result = validate_structured(fake)
    assert result.requires_confirmation is True
    assert any("Конфликт" in r or "выдуман" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_analyze_text_api_dentistry(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ocr-dent@berrio.app",
            "password": "Secret123!",
            "display_name": "OCR",
            "device_id": "ocr-dent-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    res = await client.post(
        "/api/v1/receipts/analyze-text",
        headers=headers,
        json={
            "raw_text": ("ООО Стоматология\nУслуга: лечение зуба\nИтого: 6500 руб\n"),
            "persist": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["structured"]["category_hint"]["value"] == "health"
    assert Decimal(str(body["structured"]["amount"]["value"])) == Decimal("6500.00")
    assert "пятёр" not in str(body["structured"]["merchant"]["value"] or "").lower()


@pytest.mark.asyncio
async def test_analyze_text_unreadable_needs_confirmation(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ocr-blur@berrio.app",
            "password": "Secret123!",
            "display_name": "OCR",
            "device_id": "ocr-blur-device",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    res = await client.post(
        "/api/v1/receipts/analyze-text",
        headers=headers,
        json={"raw_text": "???", "persist": True},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["requires_confirmation"] is True
    assert body["success"] is False
    assert body["status"] == "needs_confirmation"
