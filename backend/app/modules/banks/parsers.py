"""Pluggable bank email parsers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class NormalizedBankTx:
    external_id: str
    amount: Decimal
    currency: str
    merchant_raw: str
    booked_at: datetime
    direction: str  # debit|credit


class BankParser(Protocol):
    bank_code: str

    def parse(self, email_subject: str, email_body: str) -> list[NormalizedBankTx]: ...


class TinkoffParser:
    bank_code = "tinkoff"

    def parse(self, email_subject: str, email_body: str) -> list[NormalizedBankTx]:
        # Minimal stub: look for "Покупка ... 1 234,56 RUB" style lines
        import re
        from datetime import UTC

        text = f"{email_subject}\n{email_body}"
        txs: list[NormalizedBankTx] = []
        for i, match in enumerate(
            re.finditer(
                r"Покупка\s+(?P<merchant>.+?)\s+(?P<amount>[\d\s]+[.,]\d{2})\s*(?:RUB|₽)",
                text,
                re.IGNORECASE,
            )
        ):
            amount_raw = match.group("amount").replace(" ", "").replace(",", ".")
            txs.append(
                NormalizedBankTx(
                    external_id=f"tinkoff-stub-{i}-{amount_raw}",
                    amount=Decimal(amount_raw),
                    currency="RUB",
                    merchant_raw=match.group("merchant").strip(),
                    booked_at=datetime.now(UTC),
                    direction="debit",
                )
            )
        return txs


class SberParser:
    bank_code = "sber"

    def parse(self, email_subject: str, email_body: str) -> list[NormalizedBankTx]:
        import re
        from datetime import UTC

        text = f"{email_subject}\n{email_body}"
        txs: list[NormalizedBankTx] = []
        for i, match in enumerate(
            re.finditer(
                r"(?:Оплата|Покупка)\s+(?P<amount>[\d\s]+[.,]\d{2})\s*(?:RUB|р|₽).*?(?:в|магазин)?\s*(?P<merchant>[^\n]+)",
                text,
                re.IGNORECASE,
            )
        ):
            amount_raw = match.group("amount").replace(" ", "").replace(",", ".")
            txs.append(
                NormalizedBankTx(
                    external_id=f"sber-stub-{i}-{amount_raw}",
                    amount=Decimal(amount_raw),
                    currency="RUB",
                    merchant_raw=match.group("merchant").strip()[:255],
                    booked_at=datetime.now(UTC),
                    direction="debit",
                )
            )
        return txs


PARSERS: dict[str, BankParser] = {
    "tinkoff": TinkoffParser(),
    "sber": SberParser(),
    "alfa": TinkoffParser(),  # placeholder until dedicated parser
    "vtb": SberParser(),
    "other": SberParser(),
}


def get_parser(bank_code: str) -> BankParser:
    try:
        return PARSERS[bank_code.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported bank: {bank_code}") from exc
