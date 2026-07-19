"""Future Open Banking port — no credentials stored; statements today, APIs later."""

from __future__ import annotations

from typing import Protocol

from app.modules.banks.parsers import NormalizedBankTx


class BankProvider(Protocol):
    """Abstract bank data source. Statement upload implements this contract offline."""

    bank_code: str

    async def fetch_transactions(self, *, since_iso: str | None = None) -> list[NormalizedBankTx]:
        """Pull transactions from an official API when available."""
        ...


class StatementBankProvider:
    """Offline provider fed by user-uploaded statements (no login/password)."""

    def __init__(self, bank_code: str, transactions: list[NormalizedBankTx]) -> None:
        self.bank_code = bank_code
        self._txs = transactions

    async def fetch_transactions(self, *, since_iso: str | None = None) -> list[NormalizedBankTx]:
        _ = since_iso
        return list(self._txs)
