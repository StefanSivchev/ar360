"""Tests for the S3 helpers, run against moto's in-memory S3."""

import pytest

from src.land.s3 import delete_prefix, list_objects


def test_delete_prefix_removes_only_that_partition(s3, bucket):
    day1 = "raw/f/ingest_date=2026-09-01/"
    day10 = "raw/f/ingest_date=2026-09-10/part-0000.parquet"
    for key in (day1 + "part-0000.parquet", day1 + "part-0001.parquet", day10):
        s3.put_object(Bucket=bucket, Key=key, Body=b"x")

    assert delete_prefix(s3, bucket, day1) == 2
    assert list_objects(s3, bucket, "raw/") == {day10: 1}


def test_delete_prefix_refuses_prefix_without_trailing_slash(s3, bucket):
    with pytest.raises(ValueError, match="must end with"):
        delete_prefix(s3, bucket, "raw/f/ingest_date=2026-09-1")
