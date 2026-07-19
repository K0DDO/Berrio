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


def test_parse_tbank_csv_cp1251_style() -> None:
    # Typical T-Bank export headers (UTF-8 here; decoder also accepts cp1251).
    content = (
        "Дата платежа;Дата операции;Сумма платежа;Сумма операции;Категория;Описание\n"
        "18.07.2026 10:15:00;18.07.2026;-250,50;-250,50;Супермаркеты;Пятёрочка\n"
        "17.07.2026 09:00:00;17.07.2026;1000,00;1000,00;Пополнения;Перевод\n"
    ).encode("utf-8")
    txs = parse_statement_file(filename="operations.csv", content=content, bank_code="tbank")
    assert len(txs) == 2
    assert txs[0].amount == Decimal("250.50")
    assert "Пятёрочка" in txs[0].merchant_raw
