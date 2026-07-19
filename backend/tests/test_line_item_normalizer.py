"""Unit tests for receipt line name normalization."""

from app.modules.receipts.normalization import LineItemNormalizer


def test_strips_article_and_title_cases() -> None:
    n = LineItemNormalizer().normalize("№1098478218914 МОЛОКО ПРОСТОКВАШИНО")
    assert "1098478218914" not in n.name_display
    assert "Молоко" in n.name_display
    assert n.brand == "Простоквашино"


def test_extracts_volume_and_fat() -> None:
    n = LineItemNormalizer().normalize("000000123 МОЛОКО ПРОСТОКВАШИНО 2.5% 930МЛ")
    assert "000000123" not in n.name_display
    assert n.volume_label is not None
    assert "930" in (n.volume_label or "")
    assert n.fat_percent == "2.5%"
    assert n.brand == "Простоквашино"


def test_keeps_raw() -> None:
    raw = "№1 ХЛЕБ"
    n = LineItemNormalizer().normalize(raw)
    assert n.name_raw == raw
