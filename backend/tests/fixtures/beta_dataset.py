"""Beta data-quality fixtures — stores, line items, expected categories, bank txs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class StoreFixture:
    raw_names: tuple[str, ...]
    canonical: str


@dataclass(frozen=True, slots=True)
class LineItemFixture:
    name_raw: str
    expected_slug_contains: str  # category slug substring / exact child
    expect_brand: str | None = None
    expect_volume_ml: Decimal | None = None


@dataclass(frozen=True, slots=True)
class TxFixture:
    merchant_raw: str
    amount: Decimal
    note: str


# Canonical merchants used across receipt + bank reconciliation tests.
STORES: tuple[StoreFixture, ...] = (
    StoreFixture(("Пятёрочка", "PYATEROCHKA 1234", "пятерочка тц"), "Пятёрочка"),
    StoreFixture(("Магнит", "MAGNIT 55", "магнит экспресс"), "Магнит"),
    StoreFixture(("Перекресток", "перекрёсток"), "Перекрёсток"),
    StoreFixture(("WB *1234", "wildberries"), "Wildberries"),
)

# Expected categorization / product normalization cases.
LINE_ITEMS: tuple[LineItemFixture, ...] = (
    LineItemFixture(
        "Простоквашино Молоко 2.5% 930мл", "food.dairy", "Простоквашино", Decimal("930")
    ),
    LineItemFixture("Хлеб Бородинский", "food.grocery"),
    LineItemFixture("Кофе Латте", "food.cafe"),
    LineItemFixture("Книга Гарри Поттер", "growth.books"),
)

# Bank-side counterparts for reconciliation confidence checks.
TRANSACTIONS: tuple[TxFixture, ...] = (
    TxFixture("Пятёрочка", Decimal("250.00"), "exact merchant+amount"),
    TxFixture("PYATEROCHKA MOSCOW", Decimal("250.00"), "alias merchant"),
    TxFixture("Магнит", Decimal("199.90"), "different store"),
)

# Minimum accuracy threshold for the seeded categorization suite.
CATEGORIZATION_MIN_ACCURACY = 0.75
