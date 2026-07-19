"""DB-backed merchant line templates → MerchantLineParser adapters."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.merchants.templates import MerchantReceiptTemplate
from app.modules.receipts.normalization.line_item_normalizer import (
    LineItemNormalizer,
    MerchantLineParser,
    NormalizedLine,
)


class PatternMerchantParser:
    """Applies regex/contains patterns from merchant_receipt_templates."""

    def __init__(self, merchant_key: str, rows: list[MerchantReceiptTemplate]) -> None:
        self.merchant_key = merchant_key.lower()
        self._rows = sorted(rows, key=lambda r: r.priority)

    def parse(self, raw: str) -> NormalizedLine | None:
        text = raw.strip()
        for row in self._rows:
            try:
                if re.search(row.pattern, text, re.IGNORECASE):
                    display = row.name_template or text
                    # Substitute capture groups if template uses \1
                    if row.name_template and "(" in row.pattern:
                        m = re.search(row.pattern, text, re.IGNORECASE)
                        if m:
                            display = m.expand(row.name_template)
                    base = LineItemNormalizer().normalize(display)
                    return NormalizedLine(
                        name_raw=raw,
                        name_display=base.name_display,
                        brand=base.brand,
                        volume_label=base.volume_label,
                        weight_label=base.weight_label,
                        volume=base.volume,
                        weight=base.weight,
                        unit=base.unit,
                        fat_percent=base.fat_percent,
                    )
            except re.error:
                continue
        return None


async def build_normalizer(
    session: AsyncSession,
    *,
    user_id: UUID | None = None,
) -> LineItemNormalizer:
    """Load system + user templates and build a LineItemNormalizer."""
    conditions = [MerchantReceiptTemplate.user_id.is_(None)]
    if user_id is not None:
        conditions.append(MerchantReceiptTemplate.user_id == user_id)
    result = await session.execute(select(MerchantReceiptTemplate).where(or_(*conditions)))
    rows = list(result.scalars().all())
    by_key: dict[str, list[MerchantReceiptTemplate]] = {}
    for row in rows:
        by_key.setdefault(row.merchant_key.lower(), []).append(row)
    parsers: list[MerchantLineParser] = [
        PatternMerchantParser(key, items) for key, items in by_key.items()
    ]
    return LineItemNormalizer(merchant_parsers=parsers)
