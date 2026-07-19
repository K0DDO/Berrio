"""Statement CSV import smoke tests."""

from decimal import Decimal

from app.modules.banks.statement_parsers import parse_statement_file


def test_parse_simple_csv() -> None:
    content = (
        "Дата;Сумма;Описание\n" "18.07.2026;250.00;Пятёрочка\n" "17.07.2026;89.50;Кофейня\n"
    ).encode()
    txs = parse_statement_file(filename="sber.csv", content=content, bank_code="sber")
    assert len(txs) == 2
    assert txs[0].amount == Decimal("250.00")
    assert "Пятёрочка" in txs[0].merchant_raw
