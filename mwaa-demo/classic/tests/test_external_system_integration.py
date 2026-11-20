"""Unit tests for external_system_integration DAG task functions.

Tests the load_to_s3 and transform_car_data callable logic directly,
mocking boto3 S3 interactions.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# --------------------------------------------------------------------------
# load_to_s3 tests
# --------------------------------------------------------------------------


class TestLoadToS3:
    """Tests for load_to_s3 — verifies JSON output format after JSONL→JSON migration."""

    def _make_ti(self, records):
        """Create a mock TaskInstance that returns records from xcom_pull."""
        ti = MagicMock()
        ti.xcom_pull.return_value = records
        return ti

    @patch("boto3.client")
    def test_writes_json_format(self, mock_client):
        """Output body is a pretty-printed JSON array, not newline-delimited JSON."""
        from external_system_integration import load_to_s3

        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        records = [
            {"title": "Tesla Model Y", "price": 29000, "source": "car-search-api"},
            {"title": "Hyundai Ioniq 5", "price": 27500, "source": "car-search-api"},
        ]

        result = load_to_s3(
            ti=self._make_ti(records), ds="2024-06-15",
            ts_nodash="20240615T120000", ts="2024-06-15T12:00:00+00:00",
        )

        # Verify put_object was called
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]

        # Verify body is valid JSON (not JSONL)
        body = call_kwargs["Body"].decode("utf-8")
        parsed = json.loads(body)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "Tesla Model Y"

    @patch("boto3.client")
    def test_uses_json_extension(self, mock_client):
        """S3 key uses .json extension (not .jsonl)."""
        from external_system_integration import load_to_s3

        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        records = [{"title": "Car", "price": 10000}]
        load_to_s3(
            ti=self._make_ti(records), ds="2024-06-15",
            ts_nodash="20240615T120000", ts="2024-06-15T12:00:00+00:00",
        )

        call_kwargs = mock_s3.put_object.call_args[1]
        key = call_kwargs["Key"]
        assert key.endswith(".json")
        assert not key.endswith(".jsonl")
        assert key == "external-api/car-search/2024-06-15/20240615T120000.json"

    @patch("boto3.client")
    def test_content_type_is_application_json(self, mock_client):
        """ContentType is application/json (not application/x-ndjson)."""
        from external_system_integration import load_to_s3

        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        records = [{"title": "Car", "price": 10000}]
        load_to_s3(
            ti=self._make_ti(records), ds="2024-06-15",
            ts_nodash="20240615T120000", ts="2024-06-15T12:00:00+00:00",
        )

        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/json"

    @patch("boto3.client")
    def test_json_is_pretty_printed(self, mock_client):
        """Output JSON uses indent=2 for readability."""
        from external_system_integration import load_to_s3

        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        records = [{"title": "Car", "price": 10000}]
        load_to_s3(
            ti=self._make_ti(records), ds="2024-06-15",
            ts_nodash="20240615T120000", ts="2024-06-15T12:00:00+00:00",
        )

        call_kwargs = mock_s3.put_object.call_args[1]
        body = call_kwargs["Body"].decode("utf-8")

        # Pretty-printed JSON has newlines and indentation
        expected = json.dumps(records, indent=2)
        assert body == expected

    @patch("boto3.client")
    def test_empty_records_skips_upload(self, mock_client):
        """When no records exist, S3 upload is skipped."""
        from external_system_integration import load_to_s3

        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        result = load_to_s3(
            ti=self._make_ti([]), ds="2024-06-15",
            ts_nodash="20240615T120000", ts="2024-06-15T12:00:00+00:00",
        )

        mock_s3.put_object.assert_not_called()
        assert result["status"] == "skipped"
        assert result["records_written"] == 0

    @patch("boto3.client")
    def test_returns_success_metadata(self, mock_client):
        """Successful load returns status, record count, and S3 path."""
        from external_system_integration import load_to_s3

        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        records = [{"title": "Car A"}, {"title": "Car B"}, {"title": "Car C"}]
        result = load_to_s3(
            ti=self._make_ti(records), ds="2024-06-15",
            ts_nodash="20240615T120000", ts="2024-06-15T12:00:00+00:00",
        )

        assert result["status"] == "success"
        assert result["records_written"] == 3
        assert "s3://" in result["s3_path"]
        assert "2024-06-15" in result["s3_path"]


# --------------------------------------------------------------------------
# transform_car_data tests
# --------------------------------------------------------------------------


class TestTransformCarData:
    """Tests for transform_car_data — verifies transformation logic."""

    def test_transforms_api_response(self):
        """Extracts and normalises car listings from API response."""
        from external_system_integration import transform_car_data

        ti = MagicMock()
        ti.xcom_pull.return_value = {
            "results": [
                {"title": "Tesla Model Y", "price": 29000, "make": "Tesla",
                 "model": "Model Y", "year": 2024, "fuelType": "Electric"},
            ]
        }

        records = transform_car_data(ti=ti, ts="2024-06-15T12:00:00+00:00")

        assert len(records) == 1
        assert records[0]["title"] == "Tesla Model Y"
        assert records[0]["fuel_type"] == "Electric"
        assert records[0]["source"] == "car-search-api"
        assert records[0]["ingested_at"] == "2024-06-15T12:00:00+00:00"

    def test_raises_on_none_response(self):
        """Raises ValueError when API returned no data."""
        from external_system_integration import transform_car_data

        ti = MagicMock()
        ti.xcom_pull.return_value = None

        with pytest.raises(ValueError, match="No response received"):
            transform_car_data(ti=ti, ts="2024-06-15T12:00:00+00:00")

    def test_handles_string_response(self):
        """Parses JSON string response from XCom."""
        from external_system_integration import transform_car_data

        ti = MagicMock()
        ti.xcom_pull.return_value = json.dumps({
            "results": [{"title": "BMW iX", "price": 28000}]
        })

        records = transform_car_data(ti=ti, ts="2024-06-15T12:00:00+00:00")

        assert len(records) == 1
        assert records[0]["title"] == "BMW iX"

    def test_handles_items_key_response(self):
        """Handles API responses that use 'items' key instead of 'results'."""
        from external_system_integration import transform_car_data

        ti = MagicMock()
        ti.xcom_pull.return_value = {
            "items": [
                {"title": "Car A", "price": 10000},
                {"title": "Car B", "price": 20000},
            ]
        }

        records = transform_car_data(ti=ti, ts="2024-06-15T12:00:00+00:00")

        assert len(records) == 2
        assert records[0]["title"] == "Car A"
        assert records[1]["title"] == "Car B"
