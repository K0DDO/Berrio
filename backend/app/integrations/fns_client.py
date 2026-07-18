"""FNS receipt lookup — stub for Stage 3, real provider later."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FnsLineItem:
    name: str
    qty: Decimal
    price: Decimal
    sum: Decimal


@dataclass(frozen=True, slots=True)
class FnsReceiptData:
    store_name: str
    store_inn: str | None
    purchased_at: datetime
    total_amount: Decimal
    items: list[FnsLineItem]


class FnsClient:
    """
    Abstract FNS checker.

    Production: HTTP to official / partner API.
    Stage 3: deterministic stub from QR params (no photo, no external call).
    """

    async def fetch(
        self,
        *,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None = None,
        total_amount: Decimal | None = None,
    ) -> FnsReceiptData:
        raise NotImplementedError


class StubFnsClient(FnsClient):
    async def fetch(
        self,
        *,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None = None,
        total_amount: Decimal | None = None,
    ) -> FnsReceiptData:
        when = purchased_at or datetime.now(UTC)
        total = total_amount if total_amount is not None else Decimal("249.90")
        # Split into two demo lines for item pipeline testing
        milk = (total * Decimal("0.4")).quantize(Decimal("0.01"))
        bread = (total - milk).quantize(Decimal("0.01"))
        return FnsReceiptData(
            store_name="Пятёрочка",
            store_inn="7728029110",
            purchased_at=when,
            total_amount=total,
            items=[
                FnsLineItem(
                    name="Молоко Простоквашино 2.5%",
                    qty=Decimal("1"),
                    price=milk,
                    sum=milk,
                ),
                FnsLineItem(
                    name="Хлеб Бородинский",
                    qty=Decimal("1"),
                    price=bread,
                    sum=bread,
                ),
            ],
        )


def get_fns_client() -> FnsClient:
    return StubFnsClient()
