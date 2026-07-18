"""Seed script for local beta — categories + sample scan via API is preferred.

Run against a live API (after register) or import fixtures in tests:

  pytest tests/test_data_quality.py -q

Fixtures live in tests/fixtures/beta_dataset.py (stores, line items, txs).
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.fixtures.beta_dataset import LINE_ITEMS, STORES, TRANSACTIONS


def main() -> None:
    payload = {
        "stores": [{"canonical": s.canonical, "raw_names": list(s.raw_names)} for s in STORES],
        "line_items": [
            {
                "name_raw": i.name_raw,
                "expected_slug": i.expected_slug_contains,
                "brand": i.expect_brand,
                "volume_ml": str(i.expect_volume_ml) if i.expect_volume_ml else None,
            }
            for i in LINE_ITEMS
        ],
        "transactions": [
            {"merchant_raw": t.merchant_raw, "amount": str(t.amount), "note": t.note}
            for t in TRANSACTIONS
        ],
    }
    out = Path(__file__).resolve().parents[1] / "backups" / "beta_dataset.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
