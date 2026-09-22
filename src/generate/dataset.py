"""Build all six feeds: the clean truth, then the source view with defects."""

import pandas as pd

from src.common.context import RunContext
from src.generate.calendar import YEARS_OF_HISTORY, date_spine
from src.generate.customers import customers
from src.generate.defects import inject
from src.generate.disputes import disputes
from src.generate.dunning import dunning
from src.generate.fx import fx_rates
from src.generate.invoices import invoices
from src.generate.payments import cash_application

# what a customer-master extract contains; the behaviour columns are the answer key
MASTER_COLUMNS = ["customer_id", "market", "segment", "credit_grade", "terms_days", "channel"]


def clean_feeds(ctx: RunContext, years: int = YEARS_OF_HISTORY) -> dict[str, pd.DataFrame]:
    """The six feeds as they really happened, keyed by registry name."""

    cust = customers(ctx)
    dates = date_spine(ctx, years)
    inv = invoices(ctx, cust, dates)
    cash = cash_application(ctx, inv, cust)
    return {
        "sap_ar_open_items": inv,
        "cash_application": cash,
        "customer_master": cust[MASTER_COLUMNS],
        "credit_disputes": disputes(ctx, inv, cash),
        "dunning_log": dunning(ctx, inv, cash, cust),
        "fx_rates": fx_rates(ctx, dates),
    }


def source_feeds(
    ctx: RunContext, years: int = YEARS_OF_HISTORY
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, int]]]:
    """The six feeds as the source systems send them, plus the defect report."""

    return inject(clean_feeds(ctx, years), ctx)
