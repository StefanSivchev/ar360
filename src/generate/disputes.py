"""Synthetic credit disputes for AR 360 Project

One row per disputes. Disputes are selected from invvoices that settled late or not at all, so disputed invoices visibly age differently.
"""

import numpy as np
import pandas as pd

DISPUTE_RATE = 0.03  # share of positive value invoices disupted

REASONS = {
    "PRICE": 0.34,  # price on the invoice differs from the agreed list
    "QUANTITY": 0.26,  # short delivery or over delivery
    "DAMAGE": 0.18,  # good arrived damaged
    "REBATE": 0.14,  # promotional rebate not applied
    "ADMIN": 0.08,  # wrong PO, wrong entityt, missing reference
}

# mean, sd of days from raised to resolved, by reason
RESOLUTION_DAYS = {
    "PRICE": (21.0, 12.0),
    "QUANTITY": (18.0, 11.0),
    "DAMAGE": (38.0, 20.0),
    "REBATE": (45.0, 24.0),
    "ADMIN": (6.0, 4.0),
}


def settlement_lateness(invoices: pd.DataFrame, cash: pd.DataFrame) -> pd.Series:
    """Days after due date each invoice finally settled, NaN means still opened"""
    settled = cash.groupby("invoice_id").payment_date.max()
    due = invoices.set_index("invoice_id").due_date
    return (settled - due).dt.days.rename("settle_lateness")


def dispute_weight(lateness: pd.Series) -> pd.Series:
    """Relative likelihood of a dispute, by how badly the invocie settled"""
    weight = np.select(
        [lateness.isna(), lateness > 30, lateness > 0],
        [4.0, 3.0, 2.0],
        default=0.5,
    )
    return pd.Series(weight, index=lateness.index, name="dispute_weight")


def dispute_flags(
    invoices: pd.DataFrame, lateness: pd.Series, rng: np.random.Generator
) -> pd.Series:
    """Flag disputed invoices, weighted toward invoices that settled badly"""

    inv = invoices.set_index("invoice_id")
    weight = dispute_weight(lateness).reindex(inv.index)
    p = (weight / weight.mean() * DISPUTE_RATE).to_numpy()
    flag = (rng.random(len(p)) < p) & (inv.gross_amount > 0).to_numpy()
    return pd.Series(flag, index=inv.index, name="is_disputed")


def disputes(ctx, invoices: pd.DataFrame, cash: pd.DataFrame) -> pd.DataFrame:
    """Full snapshot of credit disputes, one row per dispute."""
    rng = np.random.default_rng(ctx.seed + 3)

    lateness = settlement_lateness(invoices, cash)
    flag = dispute_flags(invoices, lateness, rng)  # draw 1 - do not move

    inv = invoices.set_index("invoice_id")
    disputed = inv[flag].sort_index()
    n = len(disputed)

    reason = rng.choice(list(REASONS), n, p=list(REASONS.values()))  # draw 2
    frac = rng.uniform(0.2, 1.0, n)  # draw 3
    frac = np.where(reason == "ADMIN", 1.0, frac)

    cutoff = ctx.logical_date - pd.Timedelta(days=1)

    inv_date = disputed.invoice_date.to_numpy()
    lag = rng.integers(1, 46, n)  # draw 4
    raised = inv_date + lag.astype("timedelta64[D]")
    raised = np.minimum(raised, np.datetime64(cutoff, "D"))

    mu, sd = zip(*[RESOLUTION_DAYS[r] for r in reason])
    dur = np.clip(rng.normal(mu, sd), 1, None).round()  # draw 5
    resolved = raised + dur.astype("timedelta64[D]")
    resolved = np.where(resolved <= np.datetime64(cutoff, "D"), resolved, np.datetime64("NaT"))

    return pd.DataFrame(
        {
            "dispute_id": [f"D{i:06d}" for i in range(n)],
            "invoice_id": disputed.index,
            "customer_id": disputed.customer_id.to_numpy(),
            "reason_code": reason,
            "disp_amt": (disputed.gross_amount.to_numpy() * frac).round(2),
            "raised_date": raised,
            "resolved_date": resolved,
        }
    )
