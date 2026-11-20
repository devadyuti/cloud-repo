"""Tests for docker/app/pipeline.py ETL logic."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add docker/app/ to path so pipeline module can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "docker" / "app"))

import pipeline


class TestParseS3Path:
    """Tests for parse_s3_path utility."""

    def test_valid_path(self):
        bucket, key = pipeline.parse_s3_path("s3://my-bucket/path/to/file.parquet")
        assert bucket == "my-bucket"
        assert key == "path/to/file.parquet"

    def test_single_level_key(self):
        bucket, key = pipeline.parse_s3_path("s3://bucket/file.parquet")
        assert bucket == "bucket"
        assert key == "file.parquet"

    def test_invalid_prefix_raises(self):
        with pytest.raises(ValueError):
            pipeline.parse_s3_path("http://bucket/key")

    def test_missing_key_raises(self):
        with pytest.raises(ValueError):
            pipeline.parse_s3_path("s3://bucket-only/")

    def test_missing_bucket_raises(self):
        with pytest.raises(ValueError):
            pipeline.parse_s3_path("s3:///key")


class TestTransform:
    """Tests for the transform function."""

    def test_adds_row_index_column(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = pipeline.transform(df)
        assert "row_index" in result.columns

    def test_adds_row_index_squared_column(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = pipeline.transform(df)
        assert "row_index_squared" in result.columns

    def test_row_index_values(self):
        df = pd.DataFrame({"a": [10, 20, 30]})
        result = pipeline.transform(df)
        assert list(result["row_index"]) == [0, 1, 2]
        assert list(result["row_index_squared"]) == [0, 1, 4]

    def test_preserves_original_columns(self):
        df = pd.DataFrame({"x": [1], "y": [2]})
        result = pipeline.transform(df)
        assert "x" in result.columns
        assert "y" in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"a": [1, 2]})
        original_cols = list(df.columns)
        pipeline.transform(df)
        assert list(df.columns) == original_cols

    def test_empty_dataframe(self):
        df = pd.DataFrame({"a": []})
        result = pipeline.transform(df)
        assert len(result) == 0
        assert "row_index" in result.columns
        assert "row_index_squared" in result.columns
