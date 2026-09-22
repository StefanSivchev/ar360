"""Source system defects, applied on top of the clean feeds.

The generators produce what happened. This module produces what the
source systems send: the same data with known, counted imperfections.
The clean feeds are never modified, so every earlier test still holds.
"""

import numpy as np
import pandas as pd

from src.common.context import RunContext
from src.common.feeds import get_feed

DEFECT_RATES = {
    "duplicates": 0.005,  # overlapping extract resends the row
    "late_arrival": 0.030,  # payment posted 1-5 days after its value date
    "type_drift": 0.010,  # amount arrives as locale-formatted text
    "orphan_fk": 0.002,  # customer missing from the master extract
}
SCHEMA_DRIFT_MONTH = 30  # a new source column appears from this month of history


def _pick(rng: np.random.Generator, n: int, rate: float) -> np.ndarray:
    """Positions of exactly round(n * rate) distinct rows, in file order."""

    k = round(n * rate)
    return np.sort(rng.choice(n, size=k, replace=False))


# Defect Classes
def negatives(df: pd.DataFrame, column: str) -> tuple[pd.DataFrame, int]:
    """Credit notes already exist in the clean data: count them, change nothing."""

    return df, int((df[column] < 0).sum())


def duplicates(df: pd.DataFrame, rate: float, rng: np.random.Generator) -> tuple[pd.DataFrame, int]:
    """Resend a share of rows as exact copies, as an overlapping extract would."""

    pos = _pick(rng, len(df), rate)
    return pd.concat([df, df.iloc[pos]], ignore_index=True), len(pos)


def late_arrival(
    df: pd.DataFrame, rate: float, rng: np.random.Generator, cutoff: pd.Timestamp
) -> tuple[pd.DataFrame, int]:
    """Add the posting date; a share of payments are posted 1-5 days after value date."""

    out = df.assign(entry_date=df["payment_date"])
    eligible = np.flatnonzero(out["payment_date"] <= cutoff - pd.DateOffset(days=5))
    k = round(len(out) * rate)
    pos = np.sort(rng.choice(eligible, size=k, replace=False))
    days = rng.integers(1, 6, size=k)
    entry = out["entry_date"].to_numpy().copy()
    entry[pos] = entry[pos] + days.astype("timedelta64[D]")
    out["entry_date"] = entry
    return out, k


def orphan_fk(
    master: pd.DataFrame, rate: float, rng: np.random.Generator
) -> tuple[pd.DataFrame, int]:
    """Drop a share of customers from the master extract; their transactions become orphans."""

    pos = _pick(rng, len(master), rate)
    return master.drop(master.index[pos]).reset_index(drop=True), len(pos)


# These two test whether the pipeline parses safely and tolerates change.
def _greek(x: float) -> str:
    """1234.5 -> '1.234,50': thousands and decimal marks swapped."""

    return f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def type_drift(
    df: pd.DataFrame, column: str, rate: float, rng: np.random.Generator
) -> tuple[pd.DataFrame, int]:
    """Deliver the amount as text; a share arrives in Greek number format."""

    pos = _pick(rng, len(df), rate)
    text = np.array([f"{x:.2f}" for x in df[column]], dtype=object)
    text[pos] = [_greek(x) for x in df[column].to_numpy()[pos]]
    return df.assign(**{column: text}), len(pos)


def schema_drift(
    df: pd.DataFrame, customers: pd.DataFrame, months: int
) -> tuple[pd.DataFrame, int]:
    """From `months` into the history, the source starts sending sales_org."""

    from_date = df["invoice_date"].min() + pd.DateOffset(months=months)
    market = df["customer_id"].map(customers.set_index("customer_id")["market"])
    sales_org = (market + "01").where(df["invoice_date"] >= from_date)
    return df.assign(sales_org=sales_org), int(sales_org.notna().sum())


def inject(
    feeds: dict[str, pd.DataFrame], ctx: RunContext
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, int]]]:
    """Turn clean feeds into source feeds. Returns the new feeds and what was injected."""

    rng = np.random.default_rng(ctx.seed + 6)
    rates = DEFECT_RATES
    amount = get_feed("sap_ar_open_items").control_column
    out = dict(feeds)

    master, n_orphan = orphan_fk(out["customer_master"], rates["orphan_fk"], rng)

    inv = out["sap_ar_open_items"]
    inv, n_neg = negatives(inv, amount)
    inv, n_schema = schema_drift(inv, out["customer_master"], SCHEMA_DRIFT_MONTH)
    inv, n_type = type_drift(inv, amount, rates["type_drift"], rng)
    inv, n_dup_inv = duplicates(inv, rates["duplicates"], rng)
    cash = out["cash_application"]
    cash, n_late = late_arrival(cash, rates["late_arrival"], rng, pd.Timestamp(ctx.cutoff))
    cash, n_dup_cash = duplicates(cash, rates["duplicates"], rng)

    known = master["customer_id"]
    inv_orphans = int((~inv["customer_id"].isin(known)).sum())
    cash_orphans = int((~cash["customer_id"].isin(known)).sum())

    report = {
        "customer_master": {"orphan_fk": n_orphan},
        "sap_ar_open_items": {
            "negative": n_neg,
            "schema_drift": n_schema,
            "type_drift": n_type,
            "duplicates": n_dup_inv,
            "orphan_fk": inv_orphans,
        },
        "cash_application": {
            "late_arrival": n_late,
            "duplicates": n_dup_cash,
            "orphan_fk": cash_orphans,
        },
    }
    out.update({"customer_master": master, "sap_ar_open_items": inv, "cash_application": cash})
    return out, report
