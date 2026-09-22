"""Date for AR-360 project

One row per celndar day, it will be used to take into account the weekends, the DSO (Days Sales Outstanding),
and the building of frozen in time snapshot
"""

import pandas as pd

from src.common.context import RunContext

YEARS_OF_HISTORY = 5


def date_spine(ctx: RunContext, years: int = YEARS_OF_HISTORY) -> pd.DataFrame:
    """Calendar days from 'years' before the logical date up to the day before it"""
    end = pd.Timestamp(ctx.logical_date) - pd.DateOffset(days=1)
    start = end - pd.DateOffset(years=years) + pd.DateOffset(days=1)

    days = pd.date_range(start, end, freq="D")

    return pd.DataFrame(
        {
            "date_day": days,
            "year": days.year,
            "month": days.month,
            "day_of_week": days.dayofweek,
            "is_weekend": days.dayofweek >= 5,
            "is_month_end": days.is_month_end,
        }
    )
