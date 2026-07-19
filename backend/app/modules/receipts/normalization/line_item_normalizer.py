"""Normalize raw receipt line names into human-readable fields.

Keeps name_raw untouched; produces name_display, brand, volume/weight hints.
Merchant-specific parsers can plug in later via MerchantLineParser protocol.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

# Article / SKU markers: «№12345», «N 987654», bare long digit runs (EAN-8/13).
_ARTICLE_RE = re.compile(
    r"(?:^|\s)(?:№|N[oо]?\.?|#)\s*\d{3,}\b|\b\d{8,14}\b",
    re.IGNORECASE,
)
# Leading SKU / barcode glued to product name: «4607001234567 МОЛОКО»
_LEADING_ZEROS_SKU = re.compile(r"^\d{6,14}\s+")
# Trailing barcode or PLU after name
_TRAILING_SKU = re.compile(r"\s+\d{6,14}\s*$")
# Internal EAN-like token surrounded by spaces (keep short weights like «900»)
_INTERNAL_EAN = re.compile(r"(?<=\s)\d{8,14}(?=\s)")
_FAT_RE = re.compile(r"(\d+[.,]?\d*)\s*%")
_VOLUME_RE = re.compile(
    r"(?P<num>\d+[.,]?\d*)\s*(?P<unit>мл|ml|л|l|г|g|кг|kg)\b",
    re.IGNORECASE,
)
_MULTI_SPACE = re.compile(r"\s+")

_KNOWN_BRANDS = {
    "простоквашино": "Простоквашино",
    "домик в деревне": "Домик в деревне",
    "prostokvashino": "Простоквашино",
    "coca-cola": "Coca-Cola",
    "coca cola": "Coca-Cola",
    "pepsi": "Pepsi",
    "actimel": "Actimel",
    "danone": "Danone",
    "бородинский": "Бородинский",
}


@dataclass(frozen=True, slots=True)
class NormalizedLine:
    name_raw: str
    name_display: str
    brand: str | None = None
    volume_label: str | None = None  # e.g. "900 мл"
    weight_label: str | None = None
    volume: Decimal | None = None
    weight: Decimal | None = None
    unit: str = "pcs"
    fat_percent: str | None = None


class MerchantLineParser(Protocol):
    """Future per-merchant template (Пятёрочка, Магнит, …)."""

    merchant_key: str

    def parse(self, raw: str) -> NormalizedLine | None: ...


class LineItemNormalizer:
    """Rule-based cleaner; optional merchant parsers override when matched."""

    def __init__(self, merchant_parsers: list[MerchantLineParser] | None = None) -> None:
        self._parsers = merchant_parsers or []

    def normalize(self, raw: str, *, merchant: str | None = None) -> NormalizedLine:
        text = (raw or "").strip()
        if not text:
            return NormalizedLine(name_raw=raw or "", name_display="")

        merchant_key = (merchant or "").lower()
        for parser in self._parsers:
            if parser.merchant_key in merchant_key:
                custom = parser.parse(text)
                if custom is not None:
                    return custom

        cleaned = _ARTICLE_RE.sub(" ", text)
        cleaned = _LEADING_ZEROS_SKU.sub("", cleaned)
        cleaned = _TRAILING_SKU.sub("", cleaned)
        cleaned = _INTERNAL_EAN.sub(" ", cleaned)
        cleaned = cleaned.replace("*", " ").replace("_", " ")
        cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()

        volume = weight = None
        unit = "pcs"
        volume_label = weight_label = None
        vol_match = _VOLUME_RE.search(cleaned)
        if vol_match:
            num = Decimal(vol_match.group("num").replace(",", "."))
            u = vol_match.group("unit").lower()
            label = f"{vol_match.group('num').replace(',', '.')} {vol_match.group('unit').lower()}"
            if u in {"мл", "ml"}:
                volume, unit, volume_label = num, "ml", label.replace("ml", "мл")
            elif u in {"л", "l"}:
                volume, unit, volume_label = num * 1000, "ml", label
            elif u in {"г", "g"}:
                weight, unit, weight_label = num, "g", label.replace("g", "г")
            elif u in {"кг", "kg"}:
                weight, unit, weight_label = num * 1000, "g", label
            cleaned = (cleaned[: vol_match.start()] + cleaned[vol_match.end() :]).strip()

        fat = None
        fat_match = _FAT_RE.search(cleaned)
        if fat_match:
            fat = f"{fat_match.group(1).replace(',', '.')}%"

        brand = None
        lower = cleaned.lower()
        for key, canonical in sorted(_KNOWN_BRANDS.items(), key=lambda x: -len(x[0])):
            if key in lower:
                brand = canonical
                # Keep brand in display name; just canonicalize casing later
                break

        display = self._title_case_ru(cleaned)
        if fat and fat not in display:
            display = f"{display} {fat}".strip()

        return NormalizedLine(
            name_raw=raw,
            name_display=display or text,
            brand=brand,
            volume_label=volume_label,
            weight_label=weight_label,
            volume=volume,
            weight=weight,
            unit=unit,
            fat_percent=fat,
        )

    @staticmethod
    def _title_case_ru(text: str) -> str:
        if not text:
            return text
        # If mostly caps, rewrite; else keep mixed case lightly cleaned
        letters = [c for c in text if c.isalpha()]
        if letters and sum(1 for c in letters if c.isupper()) / len(letters) >= 0.7:
            words = text.lower().split()
            return " ".join(w[:1].upper() + w[1:] if w else "" for w in words)
        return text
