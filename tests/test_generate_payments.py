from datetime import date

import pandas as pd
import pytest

from src.common.context import RunContext
from src.common.feeds import FEEDS
from src.generate.calendar import date_spine
from src.generate.customers import customers
from src.generate.invoices import invoices
from src.generate.payments import cash_application

CTX = RunContext(logical_date=date(2026, 9, 14), seed=42)
CUTOFF = pd.Timestamp("2026-09-13")  # day before CTX.logical_date: stated, not computed


def build(ctx):
    cust = customers(ctx)
    inv = invoices(ctx, cust, date_spine(ctx))
    return inv, cash_application(ctx, inv, cust)


@pytest.fixture(scope="module")
def data():
    return build(CTX)


def test_matches_registry_contract(data):
    _, cash = data
    feed = next(f for f in FEEDS if f.name == "cash_application")
    assert feed.control_column in cash.columns
    assert not cash.duplicated(subset=list(feed.business_key)).any()


def test_cent_exact_allocation(data):
    inv, cash = data
    paid = cash.groupby("invoice_id").applied_amount.sum()
    gross = inv.set_index("invoice_id").gross_amount.loc[paid.index]
    assert ((paid * 100).round() == (gross * 100).round()).all()


def test_parts_nonzero_and_signed_like_invoice(data):
    inv, cash = data
    gross = cash.invoice_id.map(inv.set_index("invoice_id").gross_amount)
    assert (cash.applied_amount * gross > 0).all()


def test_payment_dates_between_invoice_date_and_cutoff(data):
    inv, cash = data
    invoiced = cash.invoice_id.map(inv.set_index("invoice_id").invoice_date)
    assert (cash.payment_date >= invoiced).all()
    assert (cash.payment_date <= CUTOFF).all()


def test_credit_notes_settle_once_on_due_date(data):
    inv, cash = data
    credits = inv.loc[inv.gross_amount < 0].set_index("invoice_id")
    rows = cash[cash.invoice_id.isin(credits.index)]
    assert len(rows) == len(credits)
    assert (rows.payment_date == rows.invoice_id.map(credits.due_date)).all()


def test_same_seed_same_data(data):
    _, cash = data
    pd.testing.assert_frame_equal(cash, build(CTX)[1])
