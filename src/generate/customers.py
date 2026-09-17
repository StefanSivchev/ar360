"""Synthetic customer master data file for AR-360 Project

Payment behaviour is a property of the customer, not the invoice.
"""

# The purpose of the NamedTuple is to incorporate a tuple whose positions have names.
from typing import NamedTuple

import numpy as np
import pandas as pd

from src.common.context import RunContext


class Behaviour(NamedTuple):
    """How a segment pays. Read by the payment generator later."""

    mean_days_late: float
    sd_days_late: float
    p_partial: float
    earliest_days: int


SEGMENTS: dict[str, Behaviour] = {
    "key_account": Behaviour(
        -2.0, 4.0, 0.10, -5
    ),  # key accounts pay early to take settlement discounts
    "wholesale": Behaviour(6.0, 9.0, 0.22, 0),
    "horeca": Behaviour(14.0, 16.0, 0.35, 0),
    "convenience": Behaviour(9.0, 12.0, 0.28, 0),
}

SEGMENT_MIX = (0.08, 0.34, 0.33, 0.25)  # just a mix between the segments defined earlier

# Constants defined
N_CUSTOMERS = 3_000
MARKETS = ("GR", "CY")  # meaning Greece and Cyprus
MARKET_MIX = (0.82, 0.18)
TERMS_DAYS = (0, 14, 30, 45, 60)
TERMS_MIX = (0.05, 0.15, 0.40, 0.25, 0.15)
CHANNELS = ("modern_trade", "traditional_trade", "horeca", "e_commerce")
GRADE_MIX = (0.20, 0.40, 0.30, 0.10)


def customers(ctx: RunContext, n: int = N_CUSTOMERS) -> pd.DataFrame:
    """Generate the customer master data file. The same seed produces the same DataFrame"""
    rng = np.random.default_rng(
        ctx.seed
    )  # the idea here is to ensure that if another random seed is generated it wont brake the reproductivity of the code.

    df = pd.DataFrame(
        {
            "customer_id": [
                f"C{i:06d}" for i in range(n)
            ],  # will classify the C000001 for example.
            "market": rng.choice(
                MARKETS, n, p=MARKET_MIX
            ),  # It draws the weight between the markets.
            "segment": rng.choice(list(SEGMENTS), n, p=SEGMENT_MIX),
            "credit_grade": rng.choice(
                list("ABCD"), n, p=GRADE_MIX
            ),  # limitations on the realistic synthetic data, a D-grade customer or customer who is assessed to be risky, wont get a 60 days terms, but as for the example of the project, this is a hopetical market.
            "terms_days": pd.array(rng.choice(TERMS_DAYS, n, p=TERMS_MIX), dtype="Int64"),
            "channel": rng.choice(CHANNELS, n),
        }
    )

    behaviour = pd.DataFrame(
        [SEGMENTS[s] for s in df.segment],
        columns=list(Behaviour._fields),
        index=df.index,
    )
    behaviour["mean_days_late"] = (behaviour["mean_days_late"] + rng.normal(0.0, 1.5, n)).round(2)

    return pd.concat([df, behaviour], axis=1)
