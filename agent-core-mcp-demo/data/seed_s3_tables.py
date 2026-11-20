#!/usr/bin/env python3
"""Seed S3 Tables with sample data for the AgentCore MCP demo.

Creates:
  - S3 Table Bucket: da-analytics-123456789012
  - Namespaces: customers, transactions, risk_scores
  - Iceberg tables with schemas derived from CSV data
  - Loads CSV data into tables via PyIceberg

All operations are idempotent (check-before-create pattern).

Prerequisites:
  - AWS credentials configured for eu-west-1
  - S3 Tables permissions (s3tables:*)
  - Sample CSVs generated (run generate_sample_data.py first)
  - PyIceberg installed: pip install "pyiceberg[s3fs]"

Usage:
    python -m data.seed_s3_tables                    # Seed all tables
    python -m data.seed_s3_tables --dry-run          # Preview without AWS calls
    python -m data.seed_s3_tables --bucket-name X    # Override bucket name
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

# --- Constants ---

SCRIPT_DIR = Path(__file__).parent
SAMPLE_DIR = SCRIPT_DIR / "sample"

DEFAULT_BUCKET_NAME = "da-analytics-123456789012"
DEFAULT_REGION = "eu-west-1"

# Table definitions: namespace -> table_name -> schema fields
# Each field: (name, iceberg_type, required)
TABLE_DEFINITIONS = {
    "customers": {
        "table_name": "customer_profiles",
        "csv_file": "customers.csv",
        "schema": [
            ("customer_id", "string", True),
            ("name", "string", True),
            ("segment", "string", False),
            ("region", "string", False),
            ("onboarded_date", "date", False),
            ("lifetime_value", "double", False),
        ],
    },
    "transactions": {
        "table_name": "monthly_transactions",
        "csv_file": "transactions.csv",
        "schema": [
            ("txn_id", "string", True),
            ("customer_id", "string", True),
            ("amount", "double", False),
            ("category", "string", False),
            ("txn_date", "date", False),
            ("channel", "string", False),
        ],
    },
    "risk_scores": {
        "table_name": "credit_risk_scores",
        "csv_file": "risk_scores.csv",
        "schema": [
            ("customer_id", "string", True),
            ("score", "int", False),
            ("model_version", "string", False),
            ("calculated_date", "date", False),
            ("risk_band", "string", False),
        ],
    },
}


def get_s3tables_client(region: str):
    """Create an S3 Tables boto3 client."""
    return boto3.client("s3tables", region_name=region)


# --- Table Bucket Operations ---


def find_table_bucket(client, bucket_name: str) -> str | None:
    """Find an existing table bucket by name.

    Returns the table bucket ARN if found, None otherwise.
    """
    try:
        paginator = client.get_paginator("list_table_buckets")
        for page in paginator.paginate():
            for bucket in page.get("tableBuckets", []):
                if bucket.get("name") == bucket_name:
                    arn = bucket.get("arn")
                    logger.info(f"Table bucket '{bucket_name}' exists (ARN: {arn})")
                    return arn
        return None
    except ClientError as e:
        logger.error(f"Error listing table buckets: {e}")
        raise


def create_table_bucket(client, bucket_name: str, dry_run: bool = False) -> str:
    """Create a table bucket if it doesn't exist (idempotent).

    Returns the table bucket ARN.
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would create table bucket: {bucket_name}")
        return f"arn:aws:s3tables:eu-west-1:000000000000:bucket/{bucket_name}"

    existing_arn = find_table_bucket(client, bucket_name)
    if existing_arn:
        return existing_arn

    logger.info(f"Creating table bucket '{bucket_name}'...")
    response = client.create_table_bucket(name=bucket_name)
    arn = response["arn"]
    logger.info(f"Table bucket created: {arn}")
    return arn


# --- Namespace Operations ---


def find_namespace(client, table_bucket_arn: str, namespace_name: str) -> bool:
    """Check if a namespace exists in the table bucket.

    Returns True if the namespace exists, False otherwise.
    """
    try:
        client.get_namespace(
            tableBucketARN=table_bucket_arn,
            namespace=namespace_name,
        )
        logger.info(f"Namespace '{namespace_name}' already exists")
        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NotFoundException":
            return False
        raise


def create_namespace(
    client, table_bucket_arn: str, namespace_name: str, dry_run: bool = False
) -> None:
    """Create a namespace if it doesn't exist (idempotent)."""
    if dry_run:
        logger.info(f"[DRY RUN] Would create namespace: {namespace_name}")
        return

    if find_namespace(client, table_bucket_arn, namespace_name):
        return

    logger.info(f"Creating namespace '{namespace_name}'...")
    client.create_namespace(
        tableBucketARN=table_bucket_arn,
        namespace=[namespace_name],
    )
    logger.info(f"Namespace '{namespace_name}' created")


# --- Table Operations ---


def find_table(
    client, table_bucket_arn: str, namespace: str, table_name: str
) -> str | None:
    """Check if a table exists in the given namespace.

    Returns the table ARN if found, None otherwise.
    """
    try:
        response = client.get_table(
            tableBucketARN=table_bucket_arn,
            namespace=namespace,
            name=table_name,
        )
        arn = response.get("tableARN")
        logger.info(f"Table '{namespace}.{table_name}' already exists (ARN: {arn})")
        return arn
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NotFoundException":
            return None
        raise


def build_iceberg_schema(fields: list[tuple[str, str, bool]]) -> dict:
    """Build the Iceberg schema definition for create_table.

    Args:
        fields: List of (name, type, required) tuples.

    Returns:
        Schema dict for the create_table metadata parameter.
    """
    schema_fields = []
    for field_id, (name, field_type, required) in enumerate(fields, start=1):
        schema_fields.append({
            "id": field_id,
            "name": name,
            "type": field_type,
            "required": required,
        })
    return {"fields": schema_fields}


def create_table(
    client,
    table_bucket_arn: str,
    namespace: str,
    table_name: str,
    schema_fields: list[tuple[str, str, bool]],
    dry_run: bool = False,
) -> str | None:
    """Create an Iceberg table if it doesn't exist (idempotent).

    Returns the table ARN if created or already exists.
    """
    if dry_run:
        logger.info(
            f"[DRY RUN] Would create table: {namespace}.{table_name} "
            f"({len(schema_fields)} columns)"
        )
        return None

    existing_arn = find_table(client, table_bucket_arn, namespace, table_name)
    if existing_arn:
        return existing_arn

    schema = build_iceberg_schema(schema_fields)
    logger.info(f"Creating table '{namespace}.{table_name}'...")

    response = client.create_table(
        tableBucketARN=table_bucket_arn,
        namespace=namespace,
        name=table_name,
        format="ICEBERG",
        metadata={
            "iceberg": {
                "schema": schema,
                "properties": {
                    "write.format.default": "parquet",
                    "read.split.target-size": "134217728",
                },
            }
        },
    )
    arn = response["tableARN"]
    logger.info(f"Table '{namespace}.{table_name}' created: {arn}")
    return arn


# --- Data Loading ---


def read_csv_data(csv_path: Path) -> list[dict]:
    """Read CSV data into a list of dicts."""
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        logger.error("Run 'python -m data.generate_sample_data' first to generate sample data.")
        sys.exit(1)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_data_via_pyiceberg(
    table_bucket_arn: str,
    namespace: str,
    table_name: str,
    csv_path: Path,
    schema_fields: list[tuple[str, str, bool]],
    region: str,
    dry_run: bool = False,
) -> int:
    """Load CSV data into an S3 Tables Iceberg table using PyIceberg.

    This function uses PyIceberg's REST catalog to connect to S3 Tables
    and append data from the CSV file into the target table.

    Args:
        table_bucket_arn: ARN of the S3 table bucket.
        namespace: Namespace containing the table.
        table_name: Name of the target table.
        csv_path: Path to the CSV file to load.
        schema_fields: Schema definition for type coercion.
        region: AWS region.
        dry_run: If True, skip actual data loading.

    Returns:
        Number of rows loaded.
    """
    rows = read_csv_data(csv_path)
    row_count = len(rows)

    if dry_run:
        logger.info(
            f"[DRY RUN] Would load {row_count} rows from {csv_path.name} "
            f"into {namespace}.{table_name}"
        )
        return row_count

    try:
        import pyarrow as pa
        from pyiceberg.catalog import load_catalog
    except ImportError:
        logger.warning(
            "PyIceberg or PyArrow not installed. Skipping data load.\n"
            "Install with: pip install 'pyiceberg[s3fs]' pyarrow\n"
            "Tables have been created but are empty."
        )
        return 0

    logger.info(f"Loading {row_count} rows into {namespace}.{table_name}...")

    # Connect to S3 Tables via the REST catalog endpoint
    catalog = load_catalog(
        "s3tables",
        **{
            "type": "rest",
            "uri": f"https://s3tables.{region}.amazonaws.com/iceberg",
            "rest.sigv4-enabled": "true",
            "rest.signing-region": region,
            "rest.signing-name": "s3tables",
            "warehouse": table_bucket_arn,
        },
    )

    # Load the table reference
    table = catalog.load_table(f"{namespace}.{table_name}")

    # Build PyArrow schema from our field definitions
    type_mapping = {
        "string": pa.string(),
        "int": pa.int32(),
        "long": pa.int64(),
        "float": pa.float32(),
        "double": pa.float64(),
        "boolean": pa.bool_(),
        "date": pa.date32(),
        "timestamp": pa.timestamp("us"),
        "timestamptz": pa.timestamp("us", tz="UTC"),
    }

    arrow_fields = []
    for name, field_type, required in schema_fields:
        pa_type = type_mapping.get(field_type, pa.string())
        arrow_fields.append(pa.field(name, pa_type, nullable=not required))

    arrow_schema = pa.schema(arrow_fields)

    # Convert CSV rows to typed columns
    columns = {name: [] for name, _, _ in schema_fields}
    for row in rows:
        for name, field_type, _ in schema_fields:
            raw_value = row.get(name, "")
            if field_type == "int":
                columns[name].append(int(raw_value) if raw_value else None)
            elif field_type in ("double", "float"):
                columns[name].append(float(raw_value) if raw_value else None)
            elif field_type == "boolean":
                columns[name].append(raw_value.lower() in ("true", "1", "yes") if raw_value else None)
            elif field_type == "date":
                # PyArrow date32 accepts ISO date strings
                columns[name].append(raw_value if raw_value else None)
            else:
                columns[name].append(raw_value if raw_value else None)

    # Build PyArrow arrays with proper types
    arrays = []
    for name, field_type, _ in schema_fields:
        pa_type = type_mapping.get(field_type, pa.string())
        if field_type == "date":
            # Parse date strings to date objects
            from datetime import date as date_type

            date_values = []
            for v in columns[name]:
                if v:
                    parts = v.split("-")
                    date_values.append(date_type(int(parts[0]), int(parts[1]), int(parts[2])))
                else:
                    date_values.append(None)
            arrays.append(pa.array(date_values, type=pa_type))
        else:
            arrays.append(pa.array(columns[name], type=pa_type))

    # Create the Arrow table and append to Iceberg
    arrow_table = pa.table(
        {name: arr for (name, _, _), arr in zip(schema_fields, arrays)},
        schema=arrow_schema,
    )
    table.append(arrow_table)

    logger.info(f"Successfully loaded {row_count} rows into {namespace}.{table_name}")
    return row_count


# --- Orchestration ---


def seed_all(
    bucket_name: str,
    region: str,
    dry_run: bool = False,
    skip_data_load: bool = False,
) -> None:
    """Orchestrate the full seeding process.

    Steps:
      1. Create table bucket (if not exists)
      2. Create namespaces (if not exist)
      3. Create tables with Iceberg schemas (if not exist)
      4. Load CSV data into tables via PyIceberg
    """
    logger.info("=" * 60)
    logger.info("S3 Tables Seed Script")
    logger.info("=" * 60)
    logger.info(f"  Bucket name: {bucket_name}")
    logger.info(f"  Region:      {region}")
    logger.info(f"  Dry run:     {dry_run}")
    logger.info(f"  Skip load:   {skip_data_load}")
    logger.info(f"  Sample dir:  {SAMPLE_DIR}")
    logger.info("")

    if dry_run:
        client = None
        table_bucket_arn = create_table_bucket(client, bucket_name, dry_run=True)
    else:
        client = get_s3tables_client(region)
        # Step 1: Create table bucket
        table_bucket_arn = create_table_bucket(client, bucket_name)

    logger.info("")
    logger.info("--- Creating namespaces and tables ---")

    total_rows_loaded = 0

    for namespace_name, table_def in TABLE_DEFINITIONS.items():
        logger.info("")
        logger.info(f"[{namespace_name}]")

        # Step 2: Create namespace
        create_namespace(client, table_bucket_arn, namespace_name, dry_run=dry_run)

        # Step 3: Create table
        table_name = table_def["table_name"]
        schema_fields = table_def["schema"]

        create_table(
            client, table_bucket_arn, namespace_name, table_name, schema_fields, dry_run=dry_run
        )

        # Step 4: Load data
        if not skip_data_load:
            csv_path = SAMPLE_DIR / table_def["csv_file"]
            rows_loaded = load_data_via_pyiceberg(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace_name,
                table_name=table_name,
                csv_path=csv_path,
                schema_fields=schema_fields,
                region=region,
                dry_run=dry_run,
            )
            total_rows_loaded += rows_loaded

    logger.info("")
    logger.info("=" * 60)
    logger.info("Seeding complete!")
    logger.info(f"  Table bucket ARN: {table_bucket_arn}")
    logger.info(f"  Namespaces:       {list(TABLE_DEFINITIONS.keys())}")
    logger.info(f"  Tables:           {[d['table_name'] for d in TABLE_DEFINITIONS.values()]}")
    if not skip_data_load:
        logger.info(f"  Total rows:       {total_rows_loaded}")
    logger.info("=" * 60)


def main() -> None:
    """Parse arguments and run the seed process."""
    parser = argparse.ArgumentParser(
        description="Seed S3 Tables with sample data for the AgentCore MCP demo."
    )
    parser.add_argument(
        "--bucket-name",
        default=os.environ.get("AGENTCORE_S3_TABLE_BUCKET", DEFAULT_BUCKET_NAME),
        help=f"S3 Table Bucket name (default: {DEFAULT_BUCKET_NAME})",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AGENTCORE_REGION", DEFAULT_REGION),
        help=f"AWS region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making AWS calls.",
    )
    parser.add_argument(
        "--skip-data-load",
        action="store_true",
        help="Create tables but skip loading CSV data (useful if PyIceberg is not installed).",
    )
    args = parser.parse_args()

    seed_all(
        bucket_name=args.bucket_name,
        region=args.region,
        dry_run=args.dry_run,
        skip_data_load=args.skip_data_load,
    )


if __name__ == "__main__":
    main()
