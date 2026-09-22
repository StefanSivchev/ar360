"""Synthetic ECB reference rates: units of foreign currency per 1 EUR.

Published on weekdays only, like the ECB. EUR itself has no row.
"""

import numpy as np
import pandas as pd

from src.common.context import RunContext

# currency: (rate on the first day, daily volatility of the log rate)
FX_PARAMS = {"USD": (1.18, 0.004), "GBP": (0.86, 0.003)}


def fx_rates(ctx: RunContext, dates: pd.DataFrame) -> pd.DataFrame:
    """One rate per currency per weekday of the date spine."""
    rng = np.random.default_rng(ctx.seed + 5)
    days = dates.loc[~dates["is_weekend"], "date_day"].to_numpy()
    frames = []
    for currency, (start, vol) in FX_PARAMS.items():
        steps = rng.normal(0.0, vol, len(days))
        steps[0] = 0.0
        rate = start * np.exp(np.cumsum(steps))
        frames.append(
            pd.DataFrame({"rate_date": days, "currency": currency, "rate": rate.round(4)})
        )
    return pd.concat(frames, ignore_index=True)
