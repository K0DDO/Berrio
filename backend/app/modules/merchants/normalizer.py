"""Merchant normalization — aliases → canonical name."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

_ALIASES: dict[str, str] = {
    "пятерочка": "Пятёрочка",
    "пятёрочка": "Пятёрочка",
    "pyaterochka": "Пятёрочка",
    "магнит": "Магнит",
    "magnit": "Магнит",
    "лента": "Лента",
    "lenta": "Лента",
    "перекресток": "Перекрёсток",
    "перекрёсток": "Перекрёсток",
    "vkusvill": "ВкусВилл",
    "вкусвилл": "ВкусВилл",
    "ozon": "Ozon",
    "wildberries": "Wildberries",
    "wb": "Wildberries",
}


@dataclass(frozen=True, slots=True)
class NormalizedMerchant:
    merchant_id: UUID | None
    canonical_name: str | None
    matched_alias: str | None


class MerchantNormalizer:
    """Map raw bank/receipt strings to a canonical merchant label."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self._aliases = {k.lower(): v for k, v in (aliases or _ALIASES).items()}

    async def normalize(self, raw: str) -> NormalizedMerchant:
        cleaned = " ".join(raw.strip().lower().split())
        cleaned = re.sub(r"[^a-zа-яё0-9\s]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = " ".join(cleaned.split())
        if not cleaned:
            return NormalizedMerchant(None, None, None)

        for alias, canonical in self._aliases.items():
            if alias in cleaned or cleaned in alias:
                return NormalizedMerchant(
                    merchant_id=None,
                    canonical_name=canonical,
                    matched_alias=alias,
                )

        # Title-case fallback for display / token overlap
        title = " ".join(w.capitalize() for w in cleaned.split())
        return NormalizedMerchant(
            merchant_id=None,
            canonical_name=title,
            matched_alias=cleaned,
        )
