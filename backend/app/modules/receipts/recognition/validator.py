"""Post-recognition validation — block hallucinated / inconsistent receipts."""

from __future__ import annotations

from decimal import Decimal

from app.modules.receipts.recognition.models import StructuredReceipt, ValidationResult
from app.modules.receipts.recognition.prompts import CONFIDENCE_AUTO_SAVE_THRESHOLD

_GROCERY_ITEMS = ("молоко", "хлеб", "йогурт", "кефир", "колбаса")
_GROCERY_STORES = ("пятёр", "пятер", "магнит", "лента", "перекр")
_HEALTH_HINTS = ("стоматолог", "зуб", "лечен", "клиник", "медицин", "врач")


def validate_structured(structured: StructuredReceipt) -> ValidationResult:
    reasons: list[str] = []
    merchant = (structured.merchant.value or "").lower()
    amount = structured.amount.value
    items = structured.items
    ocr = structured.raw_ocr_text.lower()

    if amount is None or amount <= 0:
        reasons.append("Сумма не найдена или равна нулю")

    if structured.overall_confidence < CONFIDENCE_AUTO_SAVE_THRESHOLD:
        reasons.append(f"Низкая уверенность распознавания ({structured.overall_confidence:.2f})")

    if structured.merchant.confidence < CONFIDENCE_AUTO_SAVE_THRESHOLD:
        reasons.append("Магазин распознан неуверенно")

    if structured.amount.confidence < CONFIDENCE_AUTO_SAVE_THRESHOLD:
        reasons.append("Сумма распознана неуверенно")

    # Hallucination: grocery store without being in OCR
    if any(s in merchant for s in _GROCERY_STORES) and not any(s in ocr for s in _GROCERY_STORES):
        reasons.append("Подозрение на выдуманный магазин (нет в OCR)")

    # Hallucination: grocery items without being in OCR
    for item in items:
        name_l = item.name.lower()
        for g in _GROCERY_ITEMS:
            if g in name_l and g not in ocr:
                reasons.append(f"Подозрение на выдуманный товар: {item.name}")
                break

    # Conflict: health OCR vs grocery merchant/items
    health_in_ocr = any(h in ocr for h in _HEALTH_HINTS)
    grocery_merchant = any(s in merchant for s in _GROCERY_STORES)
    grocery_items = any(any(g in i.name.lower() for g in _GROCERY_ITEMS) for i in items)
    if health_in_ocr and (grocery_merchant or grocery_items):
        reasons.append("Конфликт: медицинский текст vs продуктовый магазин/товары")

    # Items sum vs total (soft check)
    if amount is not None and items:
        item_sums = [i.sum for i in items if i.sum is not None]
        if item_sums:
            total_items = sum(item_sums, Decimal("0"))
            if total_items > 0 and abs(total_items - amount) > max(
                Decimal("1.00"), amount * Decimal("0.15")
            ):
                reasons.append("Сумма позиций не сходится с итогом чека")

    # Empty merchant + invented-looking items
    if not structured.merchant.value and items and not ocr.strip():
        reasons.append("Нет OCR и нет магазина — нельзя сохранять автоматически")

    requires = bool(reasons) or structured.requires_confirmation
    if not structured.success:
        return ValidationResult(
            ok=False,
            requires_confirmation=True,
            reasons=reasons or ["Не удалось уверенно распознать чек"],
            status="needs_confirmation",
        )

    if requires:
        return ValidationResult(
            ok=False,
            requires_confirmation=True,
            reasons=reasons,
            status="needs_confirmation",
        )

    return ValidationResult(ok=True, requires_confirmation=False, reasons=[], status="done")


def looks_like_hallucinated_stub(store_name: str | None, item_names: list[str]) -> bool:
    """Detect legacy stub pattern: Пятёрочка + milk/bread."""
    store = (store_name or "").lower()
    names = " ".join(item_names).lower()
    return ("пятер" in store or "пятёр" in store) and ("молоко" in names and "хлеб" in names)
