"""Tests for the partition writer, run against moto's in-memory S3."""

import io
from datetime import date

import pandas as pd

from src.common.feeds import Feed
from src.land.s3 import list_objects
from src.land.writer import write_partition

FEED = Feed("t", "append", ("id",), window_column="d")
DAY = date(2026, 9, 10)
PREFIX = "raw/t/ingest_date=2026-09-10/"


def frame(n: int) -> pd.DataFrame:
    """n rows with distinct ids."""
    return pd.DataFrame({"id": [f"k{i:03d}" for i in range(n)], "d": pd.Timestamp("2026-09-10")})


def read_back(s3, bucket, key) -> pd.DataFrame:
    """Download one landed file and read it as a frame."""
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return pd.read_parquet(io.BytesIO(body))


def test_write_lands_one_file_under_the_partition_prefix(s3, bucket):
    written = write_partition(frame(5), FEED, DAY, s3, bucket)

    assert list(written) == [PREFIX + "part-0000.snappy.parquet"]
    assert list_objects(s3, bucket, "raw/") == written


def test_writing_the_same_day_twice_leaves_identical_objects(s3, bucket):
    first = write_partition(frame(5), FEED, DAY, s3, bucket)
    second = write_partition(frame(5), FEED, DAY, s3, bucket)

    assert second == first
    assert list_objects(s3, bucket, "raw/") == first


def test_rewrite_removes_files_from_the_previous_write(s3, bucket):
    first = write_partition(frame(50), FEED, DAY, s3, bucket, target_bytes=500)
    assert len(first) > 1

    second = write_partition(frame(50), FEED, DAY, s3, bucket)

    assert len(second) == 1
    assert list_objects(s3, bucket, "raw/") == second


def test_split_files_together_hold_every_row_once(s3, bucket):
    written = write_partition(frame(50), FEED, DAY, s3, bucket, target_bytes=500)

    ids = []
    for key in written:
        ids.extend(read_back(s3, bucket, key)["id"])
    assert sorted(ids) == sorted(frame(50)["id"])
