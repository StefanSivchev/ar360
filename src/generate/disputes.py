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
