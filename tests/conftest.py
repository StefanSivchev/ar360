"""Fixtures shared by all tests."""

import boto3
import pytest
from moto import mock_aws

BUCKET = "test-lake"
REGION = "eu-central-1"


@pytest.fixture
def s3():
    """An S3 client talking to moto's in-memory S3, with one empty bucket."""
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        yield client


@pytest.fixture
def bucket(s3):
    """The name of the test bucket."""
    return BUCKET
