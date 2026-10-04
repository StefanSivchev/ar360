"""Partitioned Parquet writer for the landing zone."""

import io
from datetime import date
from math import ceil

import pandas as pd

from src.common.feeds import Feed
from src.common.logging import get_logger
from src.land.s3 import delete_prefix

# Upper bound per file. At this project's volumes a daily partition is tens of KB,
# so every partition is one file and the split only runs in tests.
TARGET_BYTES = 128 * 1024 * 1024
log = get_logger(__name__)


def partition_prefix(feed: Feed, ingest_date: date) -> str:
    """raw/<feed>/ingest_date=YYYY-MM-DD/, the agreed landing layout."""
    return f"raw/{feed.name}/ingest_date={ingest_date.isoformat()}/"


def write_partition(
    df: pd.DataFrame,
    feed: Feed,
    ingest_date: date,
    s3,
    bucket: str,
    target_bytes: int = TARGET_BYTES,
) -> dict[str, int]:
    """Replace the partition with df as snappy Parquet; return key -> bytes written."""
    prefix = partition_prefix(feed, ingest_date)
    delete_prefix(s3, bucket, prefix)

    # In-memory size overstates Parquet size, so files land under the target.
    est = int(df.memory_usage(deep=True).sum())
    parts = max(1, ceil(est / target_bytes))
    rows_per_file = max(1, ceil(len(df) / parts))

    written: dict[str, int] = {}
    for i, start in enumerate(range(0, max(len(df), 1), rows_per_file)):
        chunk = df.iloc[start : start + rows_per_file]
        buf = io.BytesIO()
        chunk.to_parquet(buf, engine="pyarrow", compression="snappy", index=False)
        body = buf.getvalue()
        key = f"{prefix}part-{i:04d}.snappy.parquet"
        s3.put_object(Bucket=bucket, Key=key, Body=body)
        written[key] = len(body)
        log.info(
            "partition_written",
            feed=feed.name,
            ingest_date=ingest_date.isoformat(),
            rows=len(df),
            files=len(written),
            size_bytes=sum(written.values()),
        )
    return written
