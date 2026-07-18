"""Receipt ↔ bank transaction matching heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from app.modules.banks.models import Transaction
from app.modules.receipts.models import Receipt

_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2}


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    receipt_id: object
    transaction_id: object
    score: Decimal
    reasons: dict


class ReconciliationEngine:
    """
    Score pairs by amount, date proximity, and merchant overlap.

    Score 0..100. Suggestions require score >= min_score (default 55).
    """

    def __init__(
        self,
        *,
        amount_tolerance: Decimal = Decimal("0.01"),
        date_window_days: int = 2,
        min_score: Decimal = Decimal("55"),
    ) -> None:
        self._amount_tolerance = amount_tolerance
        self._date_window = timedelta(days=date_window_days)
        self._min_score = min_score

    def score_pair(self, receipt: Receipt, tx: Transaction) -> MatchCandidate | None:
        if receipt.total_amount is None or receipt.purchased_at is None:
            return None

        reasons: dict = {}
        score = Decimal("0")

        # Amount (max 50): exact → 50; within 1% → 35; else fail pair
        amount_diff = abs(Decimal(str(receipt.total_amount)) - abs(Decimal(str(tx.amount))))
        if amount_diff <= self._amount_tolerance:
            score += Decimal("50")
            reasons["amount"] = "exact"
        elif receipt.total_amount > 0 and amount_diff / receipt.total_amount <= Decimal("0.01"):
            score += Decimal("35")
            reasons["amount"] = "within_1pct"
        else:
            return None

        # Date (max 30)
        delta = abs(receipt.purchased_at - tx.booked_at)
        if delta <= timedelta(hours=12):
            score += Decimal("30")
            reasons["date"] = "same_day"
        elif delta <= self._date_window:
            score += Decimal("18")
            reasons["date"] = "within_window"
        else:
            return None

        # Merchant tokens (max 20)
        r_tok = _tokens(receipt.store_name)
        t_tok = _tokens(tx.merchant_raw)
        if r_tok and t_tok:
            overlap = r_tok & t_tok
            if overlap:
                ratio = Decimal(len(overlap)) / Decimal(max(len(r_tok), len(t_tok)))
                merchant_pts = min(Decimal("20"), (ratio * Decimal("20")).quantize(Decimal("0.01")))
                score += merchant_pts
                reasons["merchant"] = {"overlap": sorted(overlap), "points": float(merchant_pts)}
            else:
                reasons["merchant"] = "no_overlap"
        else:
            reasons["merchant"] = "missing_name"

        if score < self._min_score:
            return None

        return MatchCandidate(
            receipt_id=receipt.id,
            transaction_id=tx.id,
            score=score,
            reasons=reasons,
        )

    def suggest(
        self,
        receipts: list[Receipt],
        transactions: list[Transaction],
        *,
        used_receipts: set,
        used_txs: set,
    ) -> list[MatchCandidate]:
        """Greedy best-first matching without double-booking."""
        pairs: list[MatchCandidate] = []
        for receipt in receipts:
            if receipt.id in used_receipts:
                continue
            for tx in transactions:
                if tx.id in used_txs:
                    continue
                candidate = self.score_pair(receipt, tx)
                if candidate is not None:
                    pairs.append(candidate)

        pairs.sort(key=lambda c: c.score, reverse=True)
        selected: list[MatchCandidate] = []
        taken_r: set = set(used_receipts)
        taken_t: set = set(used_txs)
        for c in pairs:
            if c.receipt_id in taken_r or c.transaction_id in taken_t:
                continue
            selected.append(c)
            taken_r.add(c.receipt_id)
            taken_t.add(c.transaction_id)
        return selected
