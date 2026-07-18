"""
Merchant normalization.

Maps raw bank/receipt strings → canonical merchants via aliases.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class NormalizedMerchant:
    merchant_id: UUID | None
    canonical_name: str | None
    matched_alias: str | None


class MerchantNormalizer:
    """Stub — Stage 7 / analytics."""

    async def normalize(self, raw: str) -> NormalizedMerchant:
        cleaned = " ".join(raw.strip().lower().split())
        return NormalizedMerchant(
            merchant_id=None,
            canonical_name=None,
            matched_alias=cleaned or None,
        )
