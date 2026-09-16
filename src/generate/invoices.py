"""Synthetic invoices for AR-360.

Volume follows a beverage seasonality curve. Due dates come from customer payment terms. A minority of lines are credit notes or non-EUR.
"""

import numpy as np
import pandas as pd

from src.common.context import RunContext

# Relative invoice volume by calendar month. The summer peak is why
# classic DSO (Days Sales Outstanding) moves with the season even when nobody pays differently.

MONTH_FACTOR = (
    0.82,  # JAN
    0.80,  # FEB
    0.92,  # MAR
    1.02,  # APR
    1.15,  # MAY
    1.28,  # JUN
    1.35,  # JUL
    1.30,  # AUG
    1.08,  # SEP
    0.95,  # OCT
    0.88,  # NOV
    0.95,  # DEC
)

BASE_PER_DAY = 400  # Weekday invoices in a month with factor 1.00
WEEKEND_FACTOR = 0.25  # Weekends trade at a quarter of weekday volume
CREDIT_NOTE_RATE = 0.04  # share of lines that are credit notes or rebates
CURRENCIES = ("EUR", "USD", "GBP")
CURRENCY_MIX = (0.94, 0.04, 0.02)  # 6% non-EUR FX conversion


def daily_counts(dates: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """nvoices per day: base x season x weekday factor, plus day-to-day noise."""
    month = dates["month"].map(lambda m: MONTH_FACTOR[m - 1])
    weekend = dates["is_weekend"].map({True: WEEKEND_FACTOR, False: 1.0})
    return rng.poisson(BASE_PER_DAY * month * weekend)


def invoices(ctx: RunContext, customers: pd.DataFrame, dates: pd.DataFrame) -> pd.DataFrame:
    """One row per invoice line for the sap_ar_open_items feed."""
    rng = np.random.default_rng(ctx.seed + 1)
    counts = daily_counts(dates, rng)
    n = int(counts.sum())
    picked = customers.iloc[rng.integers(0, len(customers), n)]
    gross = rng.lognormal(6.4, 1.1, n).round(2)
    is_credit = rng.random(n) < CREDIT_NOTE_RATE
    invoice_date = pd.Series(np.repeat(dates["date_day"].to_numpy(), counts))
    due_days = pd.Series(picked["terms_days"].array).mask(is_credit, 0)
    due_date = invoice_date + pd.to_timedelta(due_days, unit="D")

    return pd.DataFrame(
        {
            "invoice_id": [f"INV{i:07d}" for i in range(n)],
            "customer_id": picked["customer_id"].to_numpy(),
            "invoice_date": invoice_date,
            "due_date": due_date,
            "terms_days": picked["terms_days"].array,
            "gross_amount": np.where(is_credit, -gross, gross),
            "currency": rng.choice(CURRENCIES, n, p=CURRENCY_MIX),
        }
    )


# Following function returns the figures: rows, the total, the credit note, currency split


def summarise(df: pd.DataFrame) -> dict:
    """Run summary figures in plain Python types, ready to log or print"""
    credit = df["gross_amount"] < 0
    split = df["currency"].value_counts(normalize=True)
    return {
        "rows": len(df),
        "control_total": round(float(df["gross_amount"].sum()), 2),
        "credit_notes": int(credit.sum()),
        "credit_note_share": round(float(credit.mean()), 4),
        "currency_split": {cur: round(float(share), 3) for cur, share in split.items()},
        "first_date": str(df["invoice_date"].min().date()),
        "last_date": str(df["invoice_date"].max().date()),
    }
