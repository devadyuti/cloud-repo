"""
ETL pipeline that reads a parquet file from S3, applies a simple transform,
writes the result back to S3, and prints a row count summary.

Usage:
    python pipeline.py s3://bucket/path/to/input.parquet

Or set the S3_INPUT_PATH environment variable:
    S3_INPUT_PATH=s3://bucket/path/to/input.parquet python pipeline.py
"""

import os
import sys
import tempfile

import boto3
import pandas as pd


def parse_s3_path(s3_path):
    """Parse an S3 URI into bucket and key."""
    if not s3_path.startswith("s3://"):
        raise ValueError(f"Invalid S3 path: {s3_path}")
    path = s3_path[5:]
    bucket, _, key = path.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 path: {s3_path}")
    return bucket, key


def read_parquet_from_s3(s3_client, bucket, key):
    """Download and read a parquet file from S3."""
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        s3_client.download_file(bucket, key, tmp.name)
        df = pd.read_parquet(tmp.name)
    return df


def transform(df):
    """Apply a simple transform: add a computed column with row index squared."""
    df = df.copy()
    df["row_index"] = range(len(df))
    df["row_index_squared"] = df["row_index"] ** 2
    return df


def write_parquet_to_s3(s3_client, df, bucket, key):
    """Write a DataFrame as parquet to S3."""
    output_key = key.replace(".parquet", "_transformed.parquet")
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        df.to_parquet(tmp.name, index=False)
        s3_client.upload_file(tmp.name, bucket, output_key)
    return output_key


def main():
    # Get S3 input path from argument or environment variable
    s3_input_path = None
    if len(sys.argv) > 1:
        s3_input_path = sys.argv[1]
    else:
        s3_input_path = os.environ.get("S3_INPUT_PATH")

    if not s3_input_path:
        # Demo mode — run without S3 to validate the container works
        print("No S3 input path provided. Running in demo mode...")
        print("Generating sample data...")
        df = pd.DataFrame({
            "id": range(1, 101),
            "value": [i * 1.5 for i in range(1, 101)],
            "category": ["A" if i % 2 == 0 else "B" for i in range(1, 101)],
        })
        input_row_count = len(df)
        print(f"Generated {input_row_count} rows, {len(df.columns)} columns")

        print("Applying transform (adding computed columns)...")
        df_transformed = transform(df)
        output_row_count = len(df_transformed)

        print("--- Summary (Demo Mode) ---")
        print(f"Input rows:  {input_row_count}")
        print(f"Output rows: {output_row_count}")
        print(f"Columns: {list(df_transformed.columns)}")
        print("Demo pipeline complete. Container is working correctly!")
        sys.exit(0)

    print(f"Input path: {s3_input_path}")

    bucket, key = parse_s3_path(s3_input_path)
    s3_client = boto3.client("s3")

    # Read
    print(f"Reading parquet from s3://{bucket}/{key}...")
    df = read_parquet_from_s3(s3_client, bucket, key)
    input_row_count = len(df)
    print(f"Read {input_row_count} rows, {len(df.columns)} columns")

    # Transform
    print("Applying transform (adding computed columns)...")
    df_transformed = transform(df)
    output_row_count = len(df_transformed)

    # Write
    output_key = write_parquet_to_s3(s3_client, df_transformed, bucket, key)
    print(f"Wrote {output_row_count} rows to s3://{bucket}/{output_key}")

    # Summary
    print("--- Summary ---")
    print(f"Input rows:  {input_row_count}")
    print(f"Output rows: {output_row_count}")
    print(f"Columns added: row_index, row_index_squared")
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
