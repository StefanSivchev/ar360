# Holds the generator to two promises: the right shape, and byte-indentical output
# For a givenn seed, everything downstream in the project assumes both.

from datetime import date

import pandas as pd
import pytest

from src.common.context import RunContext
from src.generate.calendar import date_spine
from src.generate.customers import N_CUSTOMERS, SEGMENTS, customers


# Pytest fixture is good as any test that takes an argument called ctx get the return value of this function freshly build.
# It beats a module-level constant because each test gets its own instance and can't interfiere with one another..
@pytest.fixture
def ctx() -> RunContext:
    """A fixed run context, so every test in this file draws the same data"""
    return RunContext(logical_date=date(2026, 9, 14), seed=42)


def test_customer_master_has_expected_shape(ctx: RunContext):
    df = customers(ctx)

    assert len(df) == N_CUSTOMERS
    assert df.customer_id.is_unique
    assert set(df.segment) == set(SEGMENTS)
    assert set(df.market) == {"GR", "CY"}


def test_same_seed_produces_identical_customers(ctx: RunContext):
    """The promise every downstream test depends on"""

    first = customers(ctx)
    second = customers(ctx)

    assert pd.util.hash_pandas_object(first).sum() == (pd.util.hash_pandas_object(second).sum())


def test_behaviour_differs_within_a_segment(ctx: RunContext):
    """A per customer offset, not a segment lookup restated"""

    horeca = customers(ctx).query("segment == 'horeca'")
    assert horeca.mean_days_late.nunique() > 1
    assert horeca.sd_days_late.nunique() == 1


def test_date_spine_is_continuous_and_ends_yesterday(ctx: RunContext):
    df = date_spine(ctx)

    assert (df.date_day.diff().dt.days.dropna() == 1).all()
    assert df.date_day.max().date() == date(2026, 9, 13)
    assert df.is_month_end.sum() == 60
