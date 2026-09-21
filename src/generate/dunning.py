"""
Synthetic dunning contact log for AR-360.

One row per contact event. Append-only: events are never updated
and never re-sent. Overdue invoices accumulate contacts as they age.

"""

import numpy as np
import pandas as pd

# Days past due at which each escalation starts
TIERS = (1, 7, 14, 30, 60)

LEVELS = ("REMINDER", "FIRST_DEMAND", "SECOND_DEMAND", "FINAL_DEMAND", "ESCALATION")

# Days past due before the first contact, by segment
FIRST_CONTACT_DAYS = {
    "key_account": 3.0,
    "wholesale": 4.0,
    "horeca": 1.0,
    "convenience": 3.0,
}

PROMISE_RATE = 0.20  # Share of contacts that produce a promise to pay

# Share of promises honoured, by segment
PROMISE_KEPT = {
    "key_account": 0.88,
    "wholesale": 0.71,
    "horeca": 0.48,
    "convenience": 0.62,
}


def dunnable(
    invoices: pd.DataFrame, cash: pd.DataFrame, customers: pd.DataFrame, cutoff
) -> pd.DataFrame:
    """Invoices that went past due unpaid, with the window they can be chased in."""

    settled = cash.groupby("invoice_id").payment_date.max()
    seg = customers.set_index("customer_id").segment

    df = invoices.loc[invoices.gross_amount > 0, ["invoice_id", "customer_id", "due_date"]]

    df = df.assign(
        settled_date=df.invoice_id.map(settled),
        segment=df.customer_id.map(seg),
    )

    df["start"] = df.due_date + pd.to_timedelta(df.segment.map(FIRST_CONTACT_DAYS), unit="D")

    df["end"] = df.settled_date.fillna(pd.Timestamp(cutoff)).clip(upper=pd.Timestamp(cutoff))
    return df.loc[df.start <= df.end].reset_index(drop=True)


def contacts(dunnable_df: pd.DataFrame) -> pd.DataFrame:
    """Expand each dunnable invoice into its sequence of contact events."""

    n_tiers = len(TIERS)
    df = dunnable_df.loc[dunnable_df.index.repeat(n_tiers)].reset_index(drop=True)
    df["tier"] = np.tile(np.arange(n_tiers), len(dunnable_df))

    tier_days = np.array(TIERS, dtype="float64")[df.tier.to_numpy()]
    grace = df.segment.map(FIRST_CONTACT_DAYS).to_numpy()
    offset = np.maximum(tier_days, grace)
    df["contact_date"] = df.due_date + pd.to_timedelta(offset, unit="D")

    df = df.loc[df.contact_date.between(df.start, df.end)]
    df = df.drop_duplicates(["invoice_id", "contact_date"], keep="first")
    return df.sort_values(["invoice_id", "contact_date"]).reset_index(drop=True)


def promises(c: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Promise-to-pay per contact. Draw order is fixed: do not reorder."""

    n = len(c)
    makes = rng.random(n) < PROMISE_RATE  # 1: contact produces a promise
    keeps = rng.random(n) < c.segment.map(PROMISE_KEPT).to_numpy()  # 2: intends to keep
    u = rng.random(n)  # 3: where the date lands

    gap = (c.settled_date - c.contact_date).dt.days.to_numpy()  # NaN if still open
    is_open = np.isnan(gap)
    broken = ~keeps & (gap >= 2)

    offset = np.select(
        [is_open, broken],
        [1 + np.floor(u * 14), 1 + np.floor(u * (gap - 1))],
        default=gap + np.floor(u * 4),
    )
    promised = c.contact_date + pd.to_timedelta(offset, unit="D")
    return promised.where(makes).rename("promised_date")


def dunning(
    ctx, invoices: pd.DataFrame, cash: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    """The dunning_log feed: one row per contact, only what the source system records."""

    rng = np.random.default_rng(ctx.seed + 4)
    cutoff = pd.Timestamp(ctx.logical_date) - pd.Timedelta(days=1)

    c = contacts(dunnable(invoices, cash, customers, cutoff))
    c["promised_date"] = promises(c, rng)  # draw BEFORE any re-sort
    c["contact_level"] = np.array(LEVELS)[c.tier.to_numpy()]

    c = c.sort_values(["contact_date", "invoice_id"]).reset_index(drop=True)
    c["contact_id"] = [f"DN{i:07d}" for i in range(len(c))]
    cols = [
        "contact_id",
        "invoice_id",
        "customer_id",
        "contact_date",
        "contact_level",
        "promised_date",
    ]
    return c[cols]
