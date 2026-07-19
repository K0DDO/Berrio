"""OFD validation must not treat empty OCR as hallucination."""

from decimal import Decimal

from app.modules.receipts.recognition.models import (
    ConfidenceField,
    RecognizedItem,
    StructuredReceipt,
)
from app.modules.receipts.recognition.validator import validate_structured


def test_ofd_grocery_ticket_not_flagged_for_missing_ocr() -> None:
    structured = StructuredReceipt(
        merchant=ConfidenceField(value="Пятёрочка", confidence=0.95),
        amount=ConfidenceField(value=Decimal("250.00"), confidence=0.95),
        purchased_at=ConfidenceField(value="2026-07-10T12:00:00+03:00", confidence=0.9),
        items=[
            RecognizedItem(name="Молоко", qty=Decimal("1"), price=Decimal("100"), sum=Decimal("100"), confidence=0.9),
            RecognizedItem(name="Хлеб", qty=Decimal("1"), price=Decimal("150"), sum=Decimal("150"), confidence=0.9),
        ],
        raw_ocr_text="",
        overall_confidence=0.95,
        requires_confirmation=False,
        success=True,
    )
    result = validate_structured(structured, source="ofd")
    assert result.ok is True
    assert not any("выдуманн" in r for r in result.reasons)


def test_ocr_grocery_without_text_still_flagged() -> None:
    structured = StructuredReceipt(
        merchant=ConfidenceField(value="Пятёрочка", confidence=0.95),
        amount=ConfidenceField(value=Decimal("250.00"), confidence=0.95),
        items=[
            RecognizedItem(name="Молоко", qty=Decimal("1"), price=Decimal("100"), sum=Decimal("100")),
        ],
        raw_ocr_text="",
        overall_confidence=0.95,
        requires_confirmation=False,
        success=True,
    )
    result = validate_structured(structured, source="ocr")
    assert result.ok is False
    assert any("выдуманн" in r for r in result.reasons)
