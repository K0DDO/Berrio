"""Post-recognition validation — block hallucinated / inconsistent receipts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.modules.receipts.recognition.models import StructuredReceipt, ValidationResult
from app.modules.receipts.recognition.prompts import CONFIDENCE_AUTO_SAVE_THRESHOLD

_GROCERY_ITEMS = ("молоко", "хлеб", "йогурт", "кефир", "колбаса")
_GROCERY_STORES = ("пятёр", "пятер", "магнит", "лента", "перекр")
_HEALTH_HINTS = ("стоматолог", "зуб", "лечен", "клиник", "медицин", "врач")
_DATE_WARN_FUTURE_HOURS = 24
_DATE_WARN_OLD_DAYS = 365


def validate_structured(
    structured: StructuredReceipt,
    *,
    uploaded_at: datetime | None = None,
    source: str = "ocr",
) -> ValidationResult:
    """Validate structured receipt.

    ``source``:
      - ``ocr`` — require merchant/items to appear in raw_ocr_text when checking hallucinations
      - ``ofd`` / ``fns`` — skip OCR-presence checks (ticket comes from fiscal provider)
    """
    reasons: list[str] = []
    merchant = (structured.merchant.value or "").lower()
    amount = structured.amount.value
    items = structured.items
    ocr = structured.raw_ocr_text.lower()
    now = uploaded_at or datetime.now(UTC)
    from_ofd = source.lower() in {"ofd", "fns", "proverkacheka"}

    if amount is None or amount <= 0:
        reasons.append("Сумма не найдена или равна нулю")

    if structured.overall_confidence < CONFIDENCE_AUTO_SAVE_THRESHOLD:
        reasons.append(f"Низкая уверенность распознавания ({structured.overall_confidence:.2f})")

    if structured.merchant.confidence < CONFIDENCE_AUTO_SAVE_THRESHOLD:
        reasons.append("Магазин распознан неуверенно")

    if structured.amount.confidence < CONFIDENCE_AUTO_SAVE_THRESHOLD:
        reasons.append("Сумма распознана неуверенно")

    # OCR-only hallucination checks — do NOT apply to OFD tickets (empty raw_ocr_text).
    if not from_ofd:
        if any(s in merchant for s in _GROCERY_STORES) and not any(
            s in ocr for s in _GROCERY_STORES
        ):
            reasons.append("Подозрение на выдуманный магазин (нет в OCR)")

        for item in items:
            name_l = item.name.lower()
            for g in _GROCERY_ITEMS:
                if g in name_l and g not in ocr:
                    reasons.append(f"Подозрение на выдуманный товар: {item.name}")
                    break

        health_in_ocr = any(h in ocr for h in _HEALTH_HINTS)
        grocery_merchant = any(s in merchant for s in _GROCERY_STORES)
        grocery_items = any(any(g in i.name.lower() for g in _GROCERY_ITEMS) for i in items)
        if health_in_ocr and (grocery_merchant or grocery_items):
            reasons.append("Конфликт: медицинский текст vs продуктовый магазин/товары")

    # Always: health merchant vs grocery items
    health_merchant = any(h in merchant for h in _HEALTH_HINTS)
    grocery_items = any(any(g in i.name.lower() for g in _GROCERY_ITEMS) for i in items)
    if health_merchant and grocery_items:
        reasons.append("Конфликт: медицинский магазин vs продуктовые позиции")

    # Items sum vs total (soft check)
    if amount is not None and items:
        item_sums = [i.sum for i in items if i.sum is not None]
        if item_sums:
            total_items = sum(item_sums, Decimal("0"))
            if total_items > 0 and abs(total_items - amount) > max(
                Decimal("1.00"), amount * Decimal("0.15")
            ):
                reasons.append("Сумма позиций не сходится с итогом чека")

    # Date checks (future / ancient only — not "differs from today")
    reasons.extend(_date_warnings(structured.purchased_at.value, now=now))

    if not from_ofd and not structured.merchant.value and items and not ocr.strip():
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


def _date_warnings(raw: str | None, *, now: datetime) -> list[str]:
    if not raw:
        return []  # missing date → UI can prompt; don't block OFD auto-save
    parsed = _parse_loose_dt(raw)
    if parsed is None:
        return ["Не удалось разобрать дату покупки — проверьте дату"]
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    ref = now if now.tzinfo else now.replace(tzinfo=UTC)
    if parsed > ref + timedelta(hours=_DATE_WARN_FUTURE_HOURS):
        return ["Дата покупки в будущем — проверьте дату"]
    if parsed < ref - timedelta(days=_DATE_WARN_OLD_DAYS):
        return ["Дата покупки слишком старая — проверьте дату"]
    return []


def _parse_loose_dt(raw: str) -> datetime | None:
    text = raw.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y%m%dT%H%M%S",
        "%Y%m%dT%H%M",
    ):
        try:
            return datetime.strptime(text.replace("Z", "+0000"), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def looks_like_hallucinated_stub(store_name: str | None, item_names: list[str]) -> bool:
    """Detect legacy stub pattern: Пятёрочка + milk/bread."""
    store = (store_name or "").lower()
    names = " ".join(item_names).lower()
    return ("пятер" in store or "пятёр" in store) and ("молоко" in names and "хлеб" in names)


def build_receipt_warnings(
    *,
    store_name: str | None,
    total_amount: Decimal | None,
    purchased_at: datetime | None,
    item_names: list[str],
    item_sums: list[Decimal],
    error_message: str | None = None,
    skip_date_warnings: bool = False,
) -> list[str]:
    """Runtime warnings for API/UI after OFD or draft save."""
    warnings: list[str] = []
    if error_message:
        warnings.append(error_message)
    if looks_like_hallucinated_stub(store_name, item_names):
        warnings.append("Подозрение на некорректное распознавание магазина/товаров")
    store = (store_name or "").lower()
    if any(h in store for h in _HEALTH_HINTS) and any(
        any(g in n.lower() for g in _GROCERY_ITEMS) for n in item_names
    ):
        warnings.append("Магазин и товары выглядят несогласованно")
    if total_amount is not None and item_sums:
        total_items = sum(item_sums, Decimal("0"))
        if total_items > 0 and abs(total_items - total_amount) > max(
            Decimal("1.00"), total_amount * Decimal("0.15")
        ):
            warnings.append("Сумма позиций не сходится с итогом")
    if not skip_date_warnings:
        if purchased_at is not None:
            iso = purchased_at.isoformat()
            warnings.extend(_date_warnings(iso, now=datetime.now(UTC)))
        else:
            warnings.append("Проверьте дату")
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out
