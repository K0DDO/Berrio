"""Receipt ↔ bank transaction matching heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum

from app.modules.banks.models import Transaction
from app.modules.merchants.normalizer import MerchantNormalizer
from app.modules.receipts.models import Receipt

_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")


class MatchDecision(StrEnum):
    MATCHED = "MATCHED"
    SUGGESTED = "SUGGESTED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True, slots=True)
class MatchingWeights:
    amount: Decimal = Decimal("50")
    date: Decimal = Decimal("30")
    merchant: Decimal = Decimal("20")

    @property
    def total(self) -> Decimal:
        return self.amount + self.date + self.merchant


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    receipt_id: object
    transaction_id: object
    score: Decimal
    confidence: Decimal
    decision: MatchDecision
    reasons: dict


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2}


class ReconciliationEngine:
    """
    Score pairs by amount, date proximity, and merchant overlap.

    Weights are configurable. Confidence = score / weight_total * 100.
    Decision thresholds:
      MATCHED   >= matched_threshold (default 85)
      SUGGESTED >= min_score (default 55)
      CONFLICT  amount+date ok but merchant conflict / multi-candidate
    """

    def __init__(
        self,
        *,
        weights: MatchingWeights | None = None,
        amount_tolerance: Decimal = Decimal("0.01"),
        date_window_days: int = 2,
        min_score: Decimal = Decimal("55"),
        matched_threshold: Decimal = Decimal("85"),
        normalizer: MerchantNormalizer | None = None,
    ) -> None:
        self._weights = weights or MatchingWeights()
        self._amount_tolerance = amount_tolerance
        self._date_window = timedelta(days=date_window_days)
        self._min_score = min_score
        self._matched_threshold = matched_threshold
        self._normalizer = normalizer or MerchantNormalizer()

    async def score_pair(self, receipt: Receipt, tx: Transaction) -> MatchCandidate | None:
        if receipt.total_amount is None or receipt.purchased_at is None:
            return None

        reasons: dict = {}
        score = Decimal("0")
        w = self._weights

        amount_diff = abs(Decimal(str(receipt.total_amount)) - abs(Decimal(str(tx.amount))))
        if amount_diff <= self._amount_tolerance:
            score += w.amount
            reasons["amount"] = "exact"
        elif receipt.total_amount > 0 and amount_diff / receipt.total_amount <= Decimal("0.01"):
            score += (w.amount * Decimal("0.7")).quantize(Decimal("0.01"))
            reasons["amount"] = "within_1pct"
        else:
            return None

        delta = abs(receipt.purchased_at - tx.booked_at)
        if delta <= timedelta(hours=12):
            score += w.date
            reasons["date"] = "same_day"
        elif delta <= self._date_window:
            score += (w.date * Decimal("0.6")).quantize(Decimal("0.01"))
            reasons["date"] = "within_window"
        else:
            return None

        receipt_norm = await self._normalizer.normalize(receipt.store_name or "")
        tx_norm = await self._normalizer.normalize(tx.merchant_raw)
        r_name = receipt_norm.canonical_name or receipt.store_name
        t_name = tx_norm.canonical_name or tx.merchant_raw
        reasons["merchant_normalized"] = {
            "receipt": receipt_norm.canonical_name,
            "transaction": tx_norm.canonical_name,
        }

        r_tok = _tokens(r_name)
        t_tok = _tokens(t_name)
        merchant_conflict = False
        if r_tok and t_tok:
            overlap = r_tok & t_tok
            if overlap:
                ratio = Decimal(len(overlap)) / Decimal(max(len(r_tok), len(t_tok)))
                merchant_pts = min(w.merchant, (ratio * w.merchant).quantize(Decimal("0.01")))
                score += merchant_pts
                reasons["merchant"] = {"overlap": sorted(overlap), "points": float(merchant_pts)}
            else:
                merchant_conflict = True
                reasons["merchant"] = "conflict"
        else:
            reasons["merchant"] = "missing_name"

        confidence = (
            (score / w.total * Decimal("100")).quantize(Decimal("0.01")) if w.total > 0 else Decimal("0")
        )

        if merchant_conflict and score >= self._min_score:
            decision = MatchDecision.CONFLICT
        elif score >= self._matched_threshold:
            decision = MatchDecision.MATCHED
        elif score >= self._min_score:
            decision = MatchDecision.SUGGESTED
        else:
            return None

        return MatchCandidate(
            receipt_id=receipt.id,
            transaction_id=tx.id,
            score=score,
            confidence=confidence,
            decision=decision,
            reasons={**reasons, "confidence": float(confidence)},
        )

    async def suggest(
        self,
        receipts: list[Receipt],
        transactions: list[Transaction],
        *,
        used_receipts: set,
        used_txs: set,
    ) -> list[MatchCandidate]:
        pairs: list[MatchCandidate] = []
        for receipt in receipts:
            if receipt.id in used_receipts:
                continue
            for tx in transactions:
                if tx.id in used_txs:
                    continue
                candidate = await self.score_pair(receipt, tx)
                if candidate is not None:
                    pairs.append(candidate)

        # Detect multi-candidate conflicts for same receipt
        by_receipt: dict = {}
        for c in pairs:
            by_receipt.setdefault(c.receipt_id, []).append(c)
        resolved: list[MatchCandidate] = []
        for receipt_id, cands in by_receipt.items():
            cands.sort(key=lambda c: c.score, reverse=True)
            if len(cands) > 1 and cands[0].score - cands[1].score < Decimal("10"):
                top = cands[0]
                resolved.append(
                    MatchCandidate(
                        receipt_id=top.receipt_id,
                        transaction_id=top.transaction_id,
                        score=top.score,
                        confidence=top.confidence,
                        decision=MatchDecision.CONFLICT,
                        reasons={**top.reasons, "conflict_reason": "ambiguous_candidates"},
                    )
                )
            else:
                resolved.append(cands[0])

        resolved.sort(key=lambda c: c.score, reverse=True)
        selected: list[MatchCandidate] = []
        taken_r: set = set(used_receipts)
        taken_t: set = set(used_txs)
        for c in resolved:
            if c.receipt_id in taken_r or c.transaction_id in taken_t:
                continue
            selected.append(c)
            taken_r.add(c.receipt_id)
            taken_t.add(c.transaction_id)
        return selected
