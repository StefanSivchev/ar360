"""Synthethic cash application for AR-360 Project.

One row per payment * invoice. A payment that settles an invoice in theree parts is three rows, not one.
"""

import numpy as np
import pandas as pd

from src.common.context import RunContext

LATEST_DAYS = 180  # safety rail not a business rule
BAD_DEBT_RATE = 0.005  # average share never paid, before credit note exclusion
GRADE_RISK = {"A": 0.2, "B": 0.5, "C": 1.0, "D": 3.0}
SEGMENT_RISK = {"key_account": 0.2, "wholesale": 0.8, "horeca": 1.5, "convenience": 1.0}


def days_late(
    invoices: pd.DataFrame, customers: pd.DataFrame, rng: np.random.Generator
) -> pd.Series:
    """Days after due date each invoice is paid, drawn per customer."""

    profile = invoices[["customer_id"]].merge(
        customers[["customer_id", "mean_days_late", "sd_days_late", "earliest_days"]],
        on="customer_id",
        how="left",  # Every invoice keeps its row and picks up its customers two profile columns.
        validate="many_to_one",  # asserts that customer_id appears only once in the customer table
    )
    drawn = rng.normal(profile.mean_days_late.to_numpy(), profile.sd_days_late.to_numpy())

    clipped = np.clip(drawn, profile.earliest_days.to_numpy(), LATEST_DAYS).round()
    return pd.Series(clipped.astype("int64"), index=invoices.index, name="days_late")


def never_paid(
    invoices: pd.DataFrame, customers: pd.DataFrame, rng: np.random.Generator
) -> pd.Series:
    """Flag invoices never paid. risk weighte, credit notes excluded"""
    risk = invoices[["customer_id"]].merge(
        customers[["customer_id", "credit_grade", "segment"]],
        on="customer_id",
        how="left",
        validate="many_to_one",
    )

    weight = risk.credit_grade.map(GRADE_RISK) * risk.segment.map(SEGMENT_RISK)
    if weight.isna().any():
        raise ValueError("Credit grade or segment missing from risk tables")
    p = (weight / weight.mean() * BAD_DEBT_RATE).to_numpy()
    flag = (rng.random(len(p)) < p) & (invoices.gross_amount > 0).to_numpy()
    return pd.Series(flag, index=invoices.index, name="never_paid")


def pay_dates(
    invoices: pd.DataFrame, days_late: pd.Series, *, never: pd.Series, cutoff: pd.Timestamp
) -> pd.Series:
    """Payment date per invoice; NaT means still open at the cut-off"""
    is_credit = invoices.gross_amount < 0
    offset = days_late.where(
        ~is_credit, 0
    )  # the .where concept is to keep the value where the condition is True and replace it where the condition is False.
    raw = invoices.due_date + pd.to_timedelta(offset, unit="D")
    paid = raw.where(raw >= invoices.invoice_date, invoices.invoice_date)
    return paid.where((paid <= cutoff) & ~never).rename("pay_date")


def split_payments(
    invoices: pd.DataFrame,
    customers: pd.DataFrame,
    pay_date: pd.Series,
    rng: np.random.Generator,
) -> pd.DataFrame:
    "One row per payment * invocies, partial payers split into 2-3 parts."
    is_paid = pay_date.notna()
    cols = ["invoice_id", "customer_id", "invoice_date", "gross_amount"]
    paid = invoices.loc[is_paid, cols].assign(final_date=pay_date[is_paid])

    p = (
        paid[["customer_id"]]
        .merge(
            customers[["customer_id", "p_partial"]],
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
        .p_partial.to_numpy()
    )
    partial = (rng.random(len(paid)) < p) & (paid.gross_amount > 0).to_numpy()
    n_parts = np.where(partial, rng.integers(2, 4, len(paid)), 1)

    rows = paid.loc[paid.index.repeat(n_parts)].reset_index(drop=True)
    rows["n_parts"] = np.repeat(n_parts, n_parts)
    rows["part_no"] = rows.groupby("invoice_id").cumcount() + 1

    span = (rows.final_date - rows.invoice_date).dt.days
    step = (span * rows.part_no / rows.n_parts).round().astype("int64")
    rows["payment_date"] = rows.invoice_date + pd.to_timedelta(step, unit="D")
    return rows.drop(columns="final_date")


def allocate_amounts(rows: pd.DataFrame, rng: np.random.Generator) -> pd.Series:
    """Split each invoice's gross accross its parts, exact to the cent"""
    cents = (rows.gross_amount * 100).round().astype("int64")
    weight = pd.Series(rng.uniform(0.5, 1.5, len(rows)), index=rows.index)
    share = weight / weight.groupby(rows.invoice_id).transform("sum")
    part = np.floor(cents * share).astype("int64")
    is_last = rows.part_no == rows.n_parts
    before_last = part.where(~is_last, 0).groupby(rows.invoice_id).transform("sum")
    part = part.where(~is_last, cents - before_last)
    return (part / 100).rename("applied_amount")


def cash_application(
    ctx: RunContext, invoices: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    """Cash application feed at payment * invoice

    Owns the rng and the cut off. The call order below is load bearing: every function draws from the same generator, so reordering changes every number in the output.
    """

    rng = np.random.default_rng(ctx.seed + 2)
    cutoff = pd.Timestamp(ctx.logical_date) - pd.Timedelta(days=1)

    late = days_late(invoices, customers, rng)
    never = never_paid(invoices, customers, rng)
    pay_date = pay_dates(invoices, late, never=never, cutoff=cutoff)
    rows = split_payments(invoices, customers, pay_date, rng)
    rows["applied_amount"] = allocate_amounts(rows, rng)
    group = rows.groupby(["customer_id", "payment_date"], sort=True).ngroup()
    rows["payment_id"] = "P" + group.astype("string").str.zfill(9)

    # two parts of one invoice on the same day are one payment line: enforce the grain
    grain = ["payment_id", "invoice_id", "customer_id", "payment_date"]
    feed = rows.groupby(grain, as_index=False, sort=False).applied_amount.sum()
    feed["applied_amount"] = feed.applied_amount.round(2)
    return feed
