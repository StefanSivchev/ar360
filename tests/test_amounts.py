from decimal import Decimal

import pytest

from src.common.amounts import parse_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1277.59", "1277.59"),
        ("-45.1", "-45.1"),
        ("1.329,40", "1329.40"),
        ("654,18", "654.18"),
        ("-633,90", "-633.90"),
    ],
)
def test_text_formats_parse_exactly(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["1,234.50", "1.234", " 12.50", "12.345"])
def test_unknown_text_formats_are_rejected(raw):
    with pytest.raises(ValueError, match="unrecognised"):
        parse_amount(raw)


def test_float_passes_through_exactly():
    assert parse_amount(633.9) == Decimal("633.9")


@pytest.mark.parametrize(
    ("raw", "message"),
    [(float("nan"), "missing"), (636.90 - 424.60, "whole cents")],
)
def test_bad_floats_are_rejected(raw, message):
    with pytest.raises(ValueError, match=message):
        parse_amount(raw)


def test_mixed_total_is_signed_and_exact():
    raws = ["1277.59", "1.329,40", "-633,90", 154.16]
    assert sum(parse_amount(r) for r in raws) == Decimal("2127.25")
