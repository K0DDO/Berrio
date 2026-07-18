"""Deterministic text extraction from OCR — no invented merchants/items."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.modules.receipts.recognition.models import (
    ConfidenceField,
    RecognizedItem,
    StructuredReceipt,
)
from app.modules.receipts.recognition.prompts import CONFIDENCE_AUTO_SAVE_THRESHOLD

_AMOUNT_RE = re.compile(
    r"(?:итого|всего|сумма|к\s*оплате|total)\s*[:\-]?\s*(\d[\d\s]*[.,]?\d*)\s*(?:руб|₽|rur|rub)?",
    re.IGNORECASE,
)
_INT_AMOUNT_RE = re.compile(
    r"(?:итого|всего|сумма|к\s*оплате)\s*[:\-]?\s*(\d{3,7})\b",
    re.IGNORECASE,
)
# Explicit service total on the same line, e.g. "лечение зуба 6500"
_SERVICE_AMOUNT_RE = re.compile(
    r"(?:лечен|услуг|зуб|при[её]м).{0,60}?(\d{3,7})\b",
    re.IGNORECASE,
)

_MERCHANT_HINTS = re.compile(
    r"(ооо|зао|ао|пао|ип|стоматолог|клиник|аптек|кафе|ресторан|пятерочк|магнит|лента)",
    re.IGNORECASE,
)

_ITEM_LINE_RE = re.compile(
    r"^(.{3,80}?)\s+(\d+(?:[.,]\d+)?)\s*(?:x|×|\*)?\s*(\d+(?:[.,]\d{2})?)?\s*$",
    re.IGNORECASE,
)

_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("health", ("стоматолог", "зуб", "лечен", "клиник", "медицин", "аптек", "врач")),
    ("food", ("молоко", "хлеб", "продукт", "супермаркет", "пятерочк", "магнит", "еда")),
    ("transport", ("такси", "метро", "бензин", "азс", "яндекс.go")),
    ("home", ("хозяйств", "бытов", "ремонт")),
]


def extract_structured_from_ocr(raw_text: str) -> StructuredReceipt:
    """
    Stage 1–2: treat input as OCR text and extract only what is present.

    Never invents store names or grocery fillers.
    """
    text = (raw_text or "").strip()
    if not text or len(re.sub(r"\W+", "", text)) < 3:
        return StructuredReceipt(
            raw_ocr_text=text,
            overall_confidence=0.0,
            requires_confirmation=True,
            success=False,
            reason="Не удалось уверенно распознать чек: текст пустой или нечитаемый",
        )

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    merchant = _extract_merchant(lines)
    amount = _extract_amount(text)
    items = _extract_items(lines, amount.value)
    category = _extract_category(text)

    confidences = [
        merchant.confidence,
        amount.confidence,
        category.confidence,
        *[i.confidence for i in items],
    ]
    overall = sum(confidences) / len(confidences) if confidences else 0.0
    # Cap overall if critical fields missing
    if amount.value is None:
        overall = min(overall, 0.4)
    if merchant.value is None:
        overall = min(overall, 0.55)
    if not items and amount.value is None:
        overall = min(overall, 0.25)

    requires = overall < CONFIDENCE_AUTO_SAVE_THRESHOLD or amount.value is None
    success = amount.value is not None or bool(items) or merchant.value is not None
    reason = None
    if requires:
        reason = (
            "Не удалось уверенно распознать чек"
            if overall < CONFIDENCE_AUTO_SAVE_THRESHOLD
            else None
        )
    if not success:
        reason = "Не удалось уверенно распознать чек"

    return StructuredReceipt(
        merchant=merchant,
        amount=amount,
        items=items,
        category_hint=category,
        raw_ocr_text=text,
        overall_confidence=round(overall, 3),
        requires_confirmation=requires or not success,
        success=success,
        reason=reason,
    )


def _extract_merchant(lines: list[str]) -> ConfidenceField[str]:
    for line in lines[:8]:
        if _MERCHANT_HINTS.search(line):
            # Reject known hallucination fillers unless literally in OCR
            return ConfidenceField(value=line[:255], confidence=0.92)
    # First non-trivial line as weak merchant candidate
    for line in lines[:5]:
        if len(line) >= 4 and not re.fullmatch(r"[\d\s.,₽рубRUB]+", line, re.I):
            return ConfidenceField(value=line[:255], confidence=0.55)
    return ConfidenceField(value=None, confidence=0.1)


def _extract_amount(text: str) -> ConfidenceField[Decimal]:
    for pattern, conf in (
        (_AMOUNT_RE, 0.95),
        (_INT_AMOUNT_RE, 0.9),
        (_SERVICE_AMOUNT_RE, 0.8),
    ):
        m = pattern.search(text)
        if m:
            val = _to_decimal(m.group(1))
            if val is not None and val > 0:
                return ConfidenceField(value=val, confidence=conf)
    # Do NOT take arbitrary numbers as total — too risky
    return ConfidenceField(value=None, confidence=0.15)


def _extract_items(lines: list[str], total: Decimal | None) -> list[RecognizedItem]:
    items: list[RecognizedItem] = []
    skip = re.compile(r"итого|всего|сумма|инн|кассир|смен|чек|фн|фд|фп", re.I)
    for line in lines:
        if skip.search(line):
            continue
        # Explicit service lines like "Услуга: лечение зуба"
        if ":" in line:
            left, right = line.split(":", 1)
            name = right.strip() or left.strip()
            if len(name) >= 3 and not re.fullmatch(r"[\d\s.,]+", name):
                money = _to_decimal(right) or total
                items.append(
                    RecognizedItem(
                        name=name[:255],
                        qty=Decimal("1"),
                        price=money,
                        sum=money,
                        confidence=0.85 if money else 0.65,
                    )
                )
                continue
        m = _ITEM_LINE_RE.match(line)
        if m:
            name = m.group(1).strip()
            if _MERCHANT_HINTS.search(name) and len(name) < 40:
                continue
            qty = _to_decimal(m.group(2)) or Decimal("1")
            price = _to_decimal(m.group(3)) if m.group(3) else None
            items.append(
                RecognizedItem(
                    name=name[:255],
                    qty=qty,
                    price=price,
                    sum=(price * qty).quantize(Decimal("0.01")) if price else None,
                    confidence=0.7 if price else 0.5,
                )
            )
    # Deduplicate trivial garbage
    return [i for i in items if i.name.lower() not in {"руб", "rub", "итого"}]


def _extract_category(text: str) -> ConfidenceField[str]:
    lower = text.lower()
    for slug, keys in _CATEGORY_KEYWORDS:
        if any(k in lower for k in keys):
            # Only if keyword actually in OCR — never invent grocery for dentistry
            return ConfidenceField(value=slug, confidence=0.85)
    return ConfidenceField(value=None, confidence=0.2)


def _to_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    cleaned = raw.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
