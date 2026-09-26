"""Extraction contract: the date window every extractor filters on."""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

LOOKBACK_DAYS = 7


@dataclass(frozen=True)
class DateWindow:
    """Half-open interval: start <= d < end."""

    start: date
    end: date

    def contains(self, s: pd.Series) -> pd.Series:
        """True for values inside the window; NaT is outside."""
        return (s >= pd.Timestamp(self.start)) & (s < pd.Timestamp(self.end))


def window(logical_date: date, lookback_days: int = LOOKBACK_DAYS) -> DateWindow:
    """The run for logical_date reads that day and the lookback_days before it."""
    return DateWindow(
        start=logical_date - timedelta(days=lookback_days),
        end=logical_date + timedelta(days=1),
    )
