import pytest

from src.common.context import build_context
from src.common.feeds import FEEDS, get_feed
from src.generate.dataset import MASTER_COLUMNS, clean_feeds
from src.generate.defects import inject

# frozen from the chunk 8 run: logical date 2026-09-11, seed 42
EXPECTED_REPORT = {
    "customer_master": {"orphan_fk": 6},
    "sap_ar_open_items": {
        "negative": 24231,
        "schema_drift": 308107,
        "type_drift": 6001,
        "duplicates": 3000,
        "orphan_fk": 1205,
    },
    "cash_application": {"late_arrival": 23974, "duplicates": 3996, "orphan_fk": 1551},
}


@pytest.fixture(scope="module")
def built():
    ctx = build_context("2026-09-11", seed=42)
    clean = clean_feeds(ctx)
    source, report = inject(clean, ctx)
    return clean, source, report


def test_report_is_frozen(built):
    assert built[2] == EXPECTED_REPORT


@pytest.mark.parametrize("feed", FEEDS, ids=lambda f: f.name)
def test_feed_meets_registry_contract(built, feed):
    need = {*feed.business_key, feed.control_column} - {None}
    assert need <= set(built[1][feed.name].columns)


def test_master_ships_only_source_columns(built):
    assert list(built[1]["customer_master"].columns) == MASTER_COLUMNS


@pytest.mark.parametrize("name", ["sap_ar_open_items", "cash_application"])
def test_only_injected_duplicates_break_the_key(built, name):
    clean, source, report = built
    key = list(get_feed(name).business_key)
    assert not clean[name].duplicated(key).any()
    assert source[name].duplicated(key).sum() == report[name]["duplicates"]


def test_type_drift_changes_format_not_value(built):
    clean, source, _ = built
    amounts = clean["sap_ar_open_items"]["gross_amount"]
    text = source["sap_ar_open_items"]["gross_amount"].iloc[: len(amounts)]
    greek = text.str.contains(",", regex=False)
    fixed = text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    parsed = text.where(~greek, fixed).astype(float)
    assert (parsed.to_numpy() == amounts.to_numpy()).all()
