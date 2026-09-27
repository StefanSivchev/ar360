from datetime import date
from decimal import Decimal

import pandas as pd

from src.common.feeds import get_feed
from src.extract.base import CreditDisputesExtractor, Extractor, get_extractor, window

W = window(date(2026, 9, 11))  # [2026-09-04, 2026-09-12)


def test_delta_window_keeps_only_rows_inside_it(tmp_path):
    dates = ["2026-09-03", "2026-09-04", "2026-09-11", "2026-09-12"]
    pd.DataFrame(
        {"invoice_date": pd.to_datetime(dates), "gross_amount": ["1", "2", "3", "4"]}
    ).to_parquet(tmp_path / "sap_ar_open_items.parquet")
    got = Extractor(get_feed("sap_ar_open_items"), tmp_path).read(W)
    assert list(got["gross_amount"]) == ["2", "3"]


def test_control_total_is_signed_parses_text_and_skips_nulls(tmp_path):
    ex = Extractor(get_feed("sap_ar_open_items"), tmp_path)
    df = pd.DataFrame({"gross_amount": ["1277.59", "1.329,40", "-633,90", None]})
    assert ex.control_total(df) == Decimal("1973.09")


def test_control_total_of_empty_window_is_decimal_zero(tmp_path):
    ex = Extractor(get_feed("sap_ar_open_items"), tmp_path)
    total = ex.control_total(pd.DataFrame({"gross_amount": []}))
    assert total == 0
    assert isinstance(total, Decimal)


def test_feed_without_control_column_has_no_total(tmp_path):
    ex = Extractor(get_feed("customer_master"), tmp_path)
    assert ex.control_total(pd.DataFrame()) is None


def test_snapshot_ignores_the_window(tmp_path):
    pd.DataFrame({"customer_id": ["C1", "C2"]}).to_parquet(tmp_path / "customer_master.parquet")
    got = Extractor(get_feed("customer_master"), tmp_path).read(W)
    assert list(got["customer_id"]) == ["C1", "C2"]


def test_disputes_are_read_as_at_the_window_end(tmp_path):
    pd.DataFrame(
        {
            "dispute_id": ["D1", "D2", "D3"],
            "raised_date": pd.to_datetime(["2026-09-01", "2026-09-05", "2026-09-12"]),
            "resolved_date": pd.to_datetime(["2026-09-11", "2026-09-12", None]),
        }
    ).to_parquet(tmp_path / "credit_disputes.parquet")
    got = get_extractor(get_feed("credit_disputes"), tmp_path).read(W)
    assert list(got["dispute_id"]) == ["D1", "D2"]
    assert got["resolved_date"].iloc[0] == pd.Timestamp("2026-09-11")
    assert pd.isna(got["resolved_date"].iloc[1])


def test_get_extractor_uses_the_default_unless_special(tmp_path):
    disputes = get_extractor(get_feed("credit_disputes"), tmp_path)
    cash = get_extractor(get_feed("cash_application"), tmp_path)
    assert type(disputes) is CreditDisputesExtractor
    assert type(cash) is Extractor
