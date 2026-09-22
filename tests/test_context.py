from datetime import date

from src.common.context import build_context


def test_cutoff_is_day_before_logical_date():
    assert build_context("2026-09-14").cutoff == date(2026, 9, 13)


def test_cutoff_crosses_year_end():
    assert build_context("2026-01-01").cutoff == date(2025, 12, 31)


def test_run_id_leads_with_logical_date():
    assert build_context("2021-09-01").run_id.startswith("2021-09-01_")
