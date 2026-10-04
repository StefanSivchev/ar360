"""Extraction contract: the date window and the extractor that reads it"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd

from src.common.amounts import parse_amount
from src.common.feeds import Feed

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


@dataclass(frozen=True)
class Extractor:
    """Reads one feed from the source directory, source-faithful."""

    feed: Feed
    source_dir: Path

    def read(self, w: DateWindow) -> pd.DataFrame:
        """Delta and append feeds return the window; snapshots return all rows.

        Raises ValueError if any row has no window date: it would never be extracted.
        """
        df = pd.read_parquet(self.source_dir / f"{self.feed.name}.parquet")
        col = self.feed.window_column
        if col is not None:
            missing = int(df[col].isna().sum())
            if missing:
                raise ValueError(
                    f"{self.feed.name}: {col} is missing on {missing} row(s); "
                    "no window would ever read them"
                )
        if self.feed.load_pattern == "snapshot":
            return df
        return df[w.contains(df[self.feed.window_column])]

    def control_total(self, df: pd.DataFrame) -> Decimal | None:
        """Signed sum of the control column; None if the feed has none."""
        col = self.feed.control_column
        if col is None:
            return None
        return sum((parse_amount(v) for v in df[col].dropna()), Decimal(0))


class CreditDisputesExtractor(Extractor):
    """Disputes as they stood at the window end, not as they stand today."""

    def read(self, w: DateWindow) -> pd.DataFrame:
        """Raised before the end; resolutions on or after it are not yet known."""
        end = pd.Timestamp(w.end)
        df = super().read(w)
        df = df[df[self.feed.window_column] < end].copy()
        df.loc[df["resolved_date"] >= end, "resolved_date"] = pd.NaT
        return df


# Feeds whose source needs more than the default read.
_SPECIAL: dict[str, type[Extractor]] = {"credit_disputes": CreditDisputesExtractor}


def get_extractor(feed: Feed, source_dir: Path) -> Extractor:
    """The feed's extractor: the default unless it needs its own."""
    return _SPECIAL.get(feed.name, Extractor)(feed, source_dir)
