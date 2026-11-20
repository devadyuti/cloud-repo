"""Tests for data.seed_s3_tables module.

Uses unittest.mock to stub the s3tables boto3 client since moto does not
support S3 Tables.
"""

from unittest.mock import MagicMock, call, patch

import pytest
from botocore.exceptions import ClientError

from data.seed_s3_tables import (
    create_namespace,
    create_table_bucket,
    find_namespace,
    find_table,
    find_table_bucket,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Mocked s3tables boto3 client."""
    return MagicMock()


TABLE_BUCKET_ARN = "arn:aws:s3tables:eu-west-1:123456789012:bucket/test-bucket"


# ---------------------------------------------------------------------------
# find_namespace
# ---------------------------------------------------------------------------


class TestFindNamespace:
    def test_returns_true_when_namespace_exists(self, mock_client):
        mock_client.get_namespace.return_value = {"namespace": ["customers"]}

        result = find_namespace(mock_client, TABLE_BUCKET_ARN, "customers")

        assert result is True
        mock_client.get_namespace.assert_called_once_with(
            tableBucketARN=TABLE_BUCKET_ARN, namespace="customers"
        )

    def test_returns_false_when_not_found(self, mock_client):
        mock_client.get_namespace.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetNamespace",
        )

        result = find_namespace(mock_client, TABLE_BUCKET_ARN, "missing")

        assert result is False

    def test_raises_on_unexpected_error(self, mock_client):
        mock_client.get_namespace.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}},
            "GetNamespace",
        )

        with pytest.raises(ClientError) as exc_info:
            find_namespace(mock_client, TABLE_BUCKET_ARN, "customers")
        assert exc_info.value.response["Error"]["Code"] == "AccessDeniedException"


# ---------------------------------------------------------------------------
# create_namespace
# ---------------------------------------------------------------------------


class TestCreateNamespace:
    def test_dry_run_returns_without_aws_calls(self, mock_client):
        """dry_run=True should log and return without calling find_namespace or create."""
        create_namespace(
            mock_client, TABLE_BUCKET_ARN, "customers", dry_run=True
        )

        # The key behavioral change: in dry-run mode no AWS API calls are made
        mock_client.get_namespace.assert_not_called()
        mock_client.create_namespace.assert_not_called()

    def test_skips_creation_when_namespace_exists(self, mock_client):
        """If namespace already exists, don't attempt to create it."""
        mock_client.get_namespace.return_value = {"namespace": ["customers"]}

        create_namespace(mock_client, TABLE_BUCKET_ARN, "customers")

        mock_client.get_namespace.assert_called_once()
        mock_client.create_namespace.assert_not_called()

    def test_creates_namespace_when_not_found(self, mock_client):
        """If namespace doesn't exist, create it."""
        mock_client.get_namespace.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetNamespace",
        )

        create_namespace(mock_client, TABLE_BUCKET_ARN, "customers")

        mock_client.create_namespace.assert_called_once_with(
            tableBucketARN=TABLE_BUCKET_ARN,
            namespace=["customers"],
        )

    def test_propagates_unexpected_error_from_find(self, mock_client):
        """Non-NotFoundException errors from find_namespace should propagate."""
        mock_client.get_namespace.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Oops"}},
            "GetNamespace",
        )

        with pytest.raises(ClientError):
            create_namespace(mock_client, TABLE_BUCKET_ARN, "customers")

        mock_client.create_namespace.assert_not_called()


# ---------------------------------------------------------------------------
# find_table_bucket
# ---------------------------------------------------------------------------


class TestFindTableBucket:
    def _setup_paginator(self, mock_client, pages):
        """Configure mock paginator to yield the given pages."""
        paginator = MagicMock()
        paginator.paginate.return_value = pages
        mock_client.get_paginator.return_value = paginator

    def test_returns_arn_when_bucket_found(self, mock_client):
        self._setup_paginator(mock_client, [
            {"tableBuckets": [{"name": "test-bucket", "arn": TABLE_BUCKET_ARN}]}
        ])

        result = find_table_bucket(mock_client, "test-bucket")

        assert result == TABLE_BUCKET_ARN
        mock_client.get_paginator.assert_called_once_with("list_table_buckets")

    def test_returns_none_when_bucket_not_found(self, mock_client):
        self._setup_paginator(mock_client, [
            {"tableBuckets": [{"name": "other-bucket", "arn": "arn:aws:s3tables:eu-west-1:123:bucket/other"}]}
        ])

        result = find_table_bucket(mock_client, "test-bucket")

        assert result is None

    def test_returns_none_when_no_buckets(self, mock_client):
        self._setup_paginator(mock_client, [{"tableBuckets": []}])

        result = find_table_bucket(mock_client, "test-bucket")

        assert result is None


# ---------------------------------------------------------------------------
# create_table_bucket
# ---------------------------------------------------------------------------


class TestCreateTableBucket:
    def _setup_paginator(self, mock_client, pages):
        """Configure mock paginator to yield the given pages."""
        paginator = MagicMock()
        paginator.paginate.return_value = pages
        mock_client.get_paginator.return_value = paginator

    def test_dry_run_returns_synthetic_arn(self, mock_client):
        """dry_run=True returns a placeholder ARN without AWS calls."""
        result = create_table_bucket(mock_client, "test-bucket", dry_run=True)

        assert "test-bucket" in result
        mock_client.get_paginator.assert_not_called()
        mock_client.create_table_bucket.assert_not_called()

    def test_returns_existing_arn_when_bucket_exists(self, mock_client):
        self._setup_paginator(mock_client, [
            {"tableBuckets": [{"name": "test-bucket", "arn": TABLE_BUCKET_ARN}]}
        ])

        result = create_table_bucket(mock_client, "test-bucket")

        assert result == TABLE_BUCKET_ARN
        mock_client.create_table_bucket.assert_not_called()

    def test_creates_bucket_when_not_found(self, mock_client):
        self._setup_paginator(mock_client, [{"tableBuckets": []}])
        mock_client.create_table_bucket.return_value = {"arn": TABLE_BUCKET_ARN}

        result = create_table_bucket(mock_client, "test-bucket")

        assert result == TABLE_BUCKET_ARN
        mock_client.create_table_bucket.assert_called_once_with(name="test-bucket")


# ---------------------------------------------------------------------------
# find_table
# ---------------------------------------------------------------------------


class TestFindTable:
    def test_returns_arn_when_table_exists(self, mock_client):
        table_arn = f"{TABLE_BUCKET_ARN}/table/customers/customer_profiles"
        mock_client.get_table.return_value = {"tableARN": table_arn}

        result = find_table(mock_client, TABLE_BUCKET_ARN, "customers", "customer_profiles")

        assert result == table_arn

    def test_returns_none_when_not_found(self, mock_client):
        mock_client.get_table.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetTable",
        )

        result = find_table(mock_client, TABLE_BUCKET_ARN, "customers", "customer_profiles")

        assert result is None

    def test_raises_on_unexpected_error(self, mock_client):
        mock_client.get_table.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}},
            "GetTable",
        )

        with pytest.raises(ClientError):
            find_table(mock_client, TABLE_BUCKET_ARN, "customers", "customer_profiles")
