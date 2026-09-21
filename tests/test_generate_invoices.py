from datetime import date

import pandas as pd
import pytest

from src.common.context import RunContext
from src.common.feeds import FEEDS
from src.generate.calendar import date_spine
from src.generate.customers import customers
from src.generate.invoices import CURRENCIES, invoices

CTX = RunContext(logical_date=date(2026, 9, 14), seed=42)


def build(ctx):
    return invoices(ctx, customers(ctx), date_spine(ctx))


@pytest.fixture(scope="module")
def inv():
    return build(CTX)


def test_volume_within_5pct_of_plna(inv):
    assert abs(len(inv) - 600_000) / 600_000 < 0.05


def test_matches_registry_contract(inv):
    feed = next(
        f for f in FEEDS if f.name == "sap_ar_open_items"
    )  # This returns the first feed whose name matches. It reads the key and control column from the registry instead of retyping them, so the test check the contract rather than a copy of it.
    assert feed.control_column in inv.columns
    assert not inv.duplicated(subset=list(feed.business_key)).any()


def test_credit_notes_about_four_percent(inv):
    share = (inv.gross_amount < 0).mean()
    assert 0.035 < share < 0.045


def test_due_dates_follow_terms(inv):
    credit = inv.gross_amount < 0
    lag = (inv.due_date - inv.invoice_date).dt.days
    assert (lag[~credit] == inv.terms_days[~credit]).all()
    assert (lag[credit] == 0).all()


def test_summer_outsells_winter(inv):
    per_day = inv.groupby("invoice_date").size()
    weekday = per_day[per_day.index.dayofweek < 5]
    july = weekday[weekday.index.month == 7].mean()
    feb = weekday[weekday.index.month == 2].mean()
    assert 1.6 < july / feb < 1.8


def test_currencies_known_and_six_percent_non_eur(inv):
    assert (
        set(inv.currency) <= set(CURRENCIES)
    )  # This means every value in 'a' appears in 'b' as well so unexpected currencies fails the test.
    assert 0.055 < (inv.currency != "EUR").mean() < 0.065


def test_same_seed_same_data(inv):
    pd.testing.assert_frame_equal(
        inv, build(CTX)
    )  # Its has test and when it fails it names the column and row that differ
