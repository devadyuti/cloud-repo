#!/usr/bin/env python3
"""Seed Redshift with sample data for the AgentCore MCP demo.

Creates tables in analytics_db.public:
  - customers: Customer profile data (from customers.csv)
  - monthly_sales: Aggregated transaction data (derived from transactions.csv)
  - risk_assessments: Credit risk scores (from risk_scores.csv)

All operations are idempotent (CREATE TABLE IF NOT EXISTS).

Prerequisites:
  - AWS credentials configured for eu-west-1
  - Redshift Data API permissions (redshift-data:*)
  - For cluster mode: redshift:GetClusterCredentials permission
  - Sample CSVs generated (run generate_sample_data.py first)

Usage:
    python -m data.seed_redshift                         # Seed via cluster (default)
    python -m data.seed_redshift --mode serverless       # Seed via serverless workgroup
    python -m data.seed_redshift --dry-run               # Preview SQL without executing
    python -m data.seed_redshift --cluster-id X          # Override cluster identifier
    python -m data.seed_redshift --workgroup-name X      # Override workgroup name
"""

import argparse
import csv
import logging
import os
import sys
import time
from collections import defaultdict
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

DEFAULT_CLUSTER_ID = "anycompany-analytics"
DEFAULT_WORKGROUP_NAME = "anycompany-etl-serverless"
DEFAULT_DATABASE = "analytics_db"
DEFAULT_DB_USER = "admin"
DEFAULT_REGION = "eu-west-1"

# Batch size for INSERT statements (rows per statement)
INSERT_BATCH_SIZE = 100

# Polling interval for statement completion (seconds)
POLL_INTERVAL_SECONDS = 2
MAX_POLL_ATTEMPTS = 120  # Max ~4 minutes per statement


# --- SQL Definitions ---

CREATE_CUSTOMERS_SQL = """
CREATE TABLE IF NOT EXISTS public.customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    segment VARCHAR(30),
    region VARCHAR(30),
    onboarded_date DATE,
    lifetime_value DECIMAL(12,2)
);
"""

CREATE_MONTHLY_SALES_SQL = """
CREATE TABLE IF NOT EXISTS public.monthly_sales (
    sale_month DATE,
    category VARCHAR(30),
    total_amount DECIMAL(12,2),
    transaction_count INTEGER,
    avg_amount DECIMAL(12,2)
);
"""

CREATE_RISK_ASSESSMENTS_SQL = """
CREATE TABLE IF NOT EXISTS public.risk_assessments (
    customer_id VARCHAR(20) PRIMARY KEY,
    score INTEGER,
    model_version VARCHAR(10),
    calculated_date DATE,
    risk_band VARCHAR(20)
);
"""

TRUNCATE_CUSTOMERS_SQL = "TRUNCATE TABLE public.customers;"
TRUNCATE_MONTHLY_SALES_SQL = "TRUNCATE TABLE public.monthly_sales;"
TRUNCATE_RISK_ASSESSMENTS_SQL = "TRUNCATE TABLE public.risk_assessments;"


# --- Redshift Data API Helpers ---


def get_redshift_data_client(region: str):
    """Create a Redshift Data API boto3 client."""
    return boto3.client("redshift-data", region_name=region)


def build_execute_params(
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    sql: str,
) -> dict:
    """Build the parameters dict for execute_statement based on connection mode.

    Args:
        mode: 'cluster' or 'serverless'
        cluster_id: Redshift cluster identifier (cluster mode)
        workgroup_name: Redshift Serverless workgroup name (serverless mode)
        database: Target database name
        db_user: Database user (cluster mode only, uses IAM temp credentials)
        sql: SQL statement to execute

    Returns:
        Dict of keyword arguments for execute_statement.
    """
    params = {
        "Database": database,
        "Sql": sql,
    }

    if mode == "cluster":
        params["ClusterIdentifier"] = cluster_id
        params["DbUser"] = db_user
    else:
        params["WorkgroupName"] = workgroup_name

    return params


def execute_statement(
    client,
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    sql: str,
    description: str = "",
    dry_run: bool = False,
) -> str | None:
    """Execute a SQL statement via the Redshift Data API.

    Args:
        client: boto3 redshift-data client
        mode: 'cluster' or 'serverless'
        cluster_id: Cluster identifier
        workgroup_name: Serverless workgroup name
        database: Database name
        db_user: Database user for cluster mode
        sql: SQL to execute
        description: Human-readable description for logging
        dry_run: If True, log the SQL but don't execute

    Returns:
        Statement ID if executed, None if dry run.
    """
    label = description or sql[:60]

    if dry_run:
        logger.info(f"[DRY RUN] {label}")
        logger.debug(f"  SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")
        return None

    params = build_execute_params(mode, cluster_id, workgroup_name, database, db_user, sql)

    try:
        response = client.execute_statement(**params)
        statement_id = response["Id"]
        logger.debug(f"Statement submitted: {statement_id} ({label})")
        return statement_id
    except ClientError as e:
        logger.error(f"Failed to execute statement ({label}): {e}")
        raise


def wait_for_statement(client, statement_id: str, description: str = "") -> bool:
    """Poll describe_statement until the statement completes or fails.

    Args:
        client: boto3 redshift-data client
        statement_id: The statement ID to poll
        description: Human-readable label for logging

    Returns:
        True if statement completed successfully, False otherwise.
    """
    label = description or statement_id[:12]

    for attempt in range(MAX_POLL_ATTEMPTS):
        response = client.describe_statement(Id=statement_id)
        status = response["Status"]

        if status == "FINISHED":
            logger.debug(f"Statement completed: {label}")
            return True
        elif status == "FAILED":
            error = response.get("Error", "Unknown error")
            logger.error(f"Statement FAILED ({label}): {error}")
            return False
        elif status == "ABORTED":
            logger.error(f"Statement ABORTED ({label})")
            return False

        # Still running — wait and retry
        time.sleep(POLL_INTERVAL_SECONDS)

    logger.error(f"Statement timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s ({label})")
    return False


def execute_and_wait(
    client,
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    sql: str,
    description: str = "",
    dry_run: bool = False,
) -> bool:
    """Execute a statement and wait for completion.

    Args:
        client: boto3 redshift-data client
        mode: 'cluster' or 'serverless'
        cluster_id: Cluster identifier
        workgroup_name: Serverless workgroup name
        database: Database name
        db_user: Database user for cluster mode
        sql: SQL to execute
        description: Human-readable description
        dry_run: If True, log without executing

    Returns:
        True if successful (or dry run), False on failure.
    """
    statement_id = execute_statement(
        client, mode, cluster_id, workgroup_name, database, db_user, sql, description, dry_run
    )

    if dry_run:
        return True

    return wait_for_statement(client, statement_id, description)


# --- CSV Reading ---


def read_csv_data(csv_path: Path) -> list[dict]:
    """Read CSV data into a list of dicts."""
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        logger.error("Run 'python -m data.generate_sample_data' first to generate sample data.")
        sys.exit(1)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


# --- Data Transformation ---


def aggregate_monthly_sales(transactions: list[dict]) -> list[dict]:
    """Aggregate transaction data into monthly sales by category.

    Groups transactions by (year-month, category) and computes:
      - total_amount: sum of all transaction amounts
      - transaction_count: number of transactions
      - avg_amount: average transaction amount

    Args:
        transactions: List of transaction dicts from CSV.

    Returns:
        List of monthly sales aggregate dicts.
    """
    # Group by (month, category)
    groups = defaultdict(lambda: {"total": 0.0, "count": 0})

    for txn in transactions:
        txn_date = txn.get("txn_date", "")
        category = txn.get("category", "Unknown")
        amount_str = txn.get("amount", "0")

        if not txn_date or not amount_str:
            continue

        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            continue

        # Extract year-month as first of month
        date_parts = txn_date.split("-")
        if len(date_parts) >= 2:
            sale_month = f"{date_parts[0]}-{date_parts[1]}-01"
        else:
            continue

        key = (sale_month, category)
        groups[key]["total"] += amount
        groups[key]["count"] += 1

    # Build result list
    results = []
    for (sale_month, category), agg in sorted(groups.items()):
        avg_amount = agg["total"] / agg["count"] if agg["count"] > 0 else 0.0
        results.append({
            "sale_month": sale_month,
            "category": category,
            "total_amount": round(agg["total"], 2),
            "transaction_count": agg["count"],
            "avg_amount": round(avg_amount, 2),
        })

    return results


# --- SQL Generation ---


def escape_sql_string(value: str) -> str:
    """Escape single quotes in a SQL string value."""
    if value is None:
        return "NULL"
    return value.replace("'", "''")


def build_customers_insert(rows: list[dict]) -> str:
    """Build an INSERT statement for a batch of customer rows."""
    values_parts = []
    for row in rows:
        customer_id = escape_sql_string(row.get("customer_id", ""))
        name = escape_sql_string(row.get("name", ""))
        segment = escape_sql_string(row.get("segment", ""))
        region = escape_sql_string(row.get("region", ""))
        onboarded_date = row.get("onboarded_date", "")
        lifetime_value = row.get("lifetime_value", "0")

        date_val = f"'{onboarded_date}'" if onboarded_date else "NULL"
        lv_val = lifetime_value if lifetime_value else "0"

        values_parts.append(
            f"('{customer_id}', '{name}', '{segment}', '{region}', {date_val}, {lv_val})"
        )

    values_sql = ",\n".join(values_parts)
    return (
        "INSERT INTO public.customers "
        "(customer_id, name, segment, region, onboarded_date, lifetime_value)\n"
        f"VALUES\n{values_sql};"
    )


def build_monthly_sales_insert(rows: list[dict]) -> str:
    """Build an INSERT statement for a batch of monthly sales rows."""
    values_parts = []
    for row in rows:
        sale_month = row.get("sale_month", "")
        category = escape_sql_string(row.get("category", ""))
        total_amount = row.get("total_amount", 0)
        transaction_count = row.get("transaction_count", 0)
        avg_amount = row.get("avg_amount", 0)

        date_val = f"'{sale_month}'" if sale_month else "NULL"

        values_parts.append(
            f"({date_val}, '{category}', {total_amount}, {transaction_count}, {avg_amount})"
        )

    values_sql = ",\n".join(values_parts)
    return (
        "INSERT INTO public.monthly_sales "
        "(sale_month, category, total_amount, transaction_count, avg_amount)\n"
        f"VALUES\n{values_sql};"
    )


def build_risk_assessments_insert(rows: list[dict]) -> str:
    """Build an INSERT statement for a batch of risk assessment rows."""
    values_parts = []
    for row in rows:
        customer_id = escape_sql_string(row.get("customer_id", ""))
        score = row.get("score", "0")
        model_version = escape_sql_string(row.get("model_version", ""))
        calculated_date = row.get("calculated_date", "")
        risk_band = escape_sql_string(row.get("risk_band", ""))

        score_val = int(score) if score else 0
        date_val = f"'{calculated_date}'" if calculated_date else "NULL"

        values_parts.append(
            f"('{customer_id}', {score_val}, '{model_version}', {date_val}, '{risk_band}')"
        )

    values_sql = ",\n".join(values_parts)
    return (
        "INSERT INTO public.risk_assessments "
        "(customer_id, score, model_version, calculated_date, risk_band)\n"
        f"VALUES\n{values_sql};"
    )


# --- Data Loading ---


def load_customers(
    client,
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    dry_run: bool = False,
) -> int:
    """Load customer data from CSV into Redshift.

    Returns the number of rows loaded.
    """
    csv_path = SAMPLE_DIR / "customers.csv"
    rows = read_csv_data(csv_path)
    total_rows = len(rows)

    logger.info(f"Loading {total_rows} customer rows (batch size: {INSERT_BATCH_SIZE})...")

    for i in range(0, total_rows, INSERT_BATCH_SIZE):
        batch = rows[i : i + INSERT_BATCH_SIZE]
        sql = build_customers_insert(batch)
        batch_num = (i // INSERT_BATCH_SIZE) + 1
        total_batches = (total_rows + INSERT_BATCH_SIZE - 1) // INSERT_BATCH_SIZE

        success = execute_and_wait(
            client, mode, cluster_id, workgroup_name, database, db_user,
            sql, description=f"INSERT customers batch {batch_num}/{total_batches}",
            dry_run=dry_run,
        )
        if not success and not dry_run:
            logger.error(f"Failed to load customers batch {batch_num}")
            return i  # Return rows loaded so far

    logger.info(f"Loaded {total_rows} rows into public.customers")
    return total_rows


def load_monthly_sales(
    client,
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    dry_run: bool = False,
) -> int:
    """Load aggregated monthly sales data from transactions CSV into Redshift.

    Aggregates transactions by month and category before inserting.
    Returns the number of rows loaded.
    """
    csv_path = SAMPLE_DIR / "transactions.csv"
    transactions = read_csv_data(csv_path)

    logger.info(f"Aggregating {len(transactions)} transactions into monthly sales...")
    monthly_sales = aggregate_monthly_sales(transactions)
    total_rows = len(monthly_sales)
    logger.info(f"Generated {total_rows} monthly sales aggregates")

    for i in range(0, total_rows, INSERT_BATCH_SIZE):
        batch = monthly_sales[i : i + INSERT_BATCH_SIZE]
        sql = build_monthly_sales_insert(batch)
        batch_num = (i // INSERT_BATCH_SIZE) + 1
        total_batches = (total_rows + INSERT_BATCH_SIZE - 1) // INSERT_BATCH_SIZE

        success = execute_and_wait(
            client, mode, cluster_id, workgroup_name, database, db_user,
            sql, description=f"INSERT monthly_sales batch {batch_num}/{total_batches}",
            dry_run=dry_run,
        )
        if not success and not dry_run:
            logger.error(f"Failed to load monthly_sales batch {batch_num}")
            return i

    logger.info(f"Loaded {total_rows} rows into public.monthly_sales")
    return total_rows


def load_risk_assessments(
    client,
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    dry_run: bool = False,
) -> int:
    """Load risk assessment data from CSV into Redshift.

    Returns the number of rows loaded.
    """
    csv_path = SAMPLE_DIR / "risk_scores.csv"
    rows = read_csv_data(csv_path)
    total_rows = len(rows)

    logger.info(f"Loading {total_rows} risk assessment rows (batch size: {INSERT_BATCH_SIZE})...")

    for i in range(0, total_rows, INSERT_BATCH_SIZE):
        batch = rows[i : i + INSERT_BATCH_SIZE]
        sql = build_risk_assessments_insert(batch)
        batch_num = (i // INSERT_BATCH_SIZE) + 1
        total_batches = (total_rows + INSERT_BATCH_SIZE - 1) // INSERT_BATCH_SIZE

        success = execute_and_wait(
            client, mode, cluster_id, workgroup_name, database, db_user,
            sql, description=f"INSERT risk_assessments batch {batch_num}/{total_batches}",
            dry_run=dry_run,
        )
        if not success and not dry_run:
            logger.error(f"Failed to load risk_assessments batch {batch_num}")
            return i

    logger.info(f"Loaded {total_rows} rows into public.risk_assessments")
    return total_rows


# --- Verification ---


def verify_table_counts(
    client,
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
) -> dict[str, int]:
    """Run SELECT COUNT(*) on each table and return row counts.

    Returns:
        Dict mapping table name to row count.
    """
    tables = ["public.customers", "public.monthly_sales", "public.risk_assessments"]
    counts = {}

    for table in tables:
        sql = f"SELECT COUNT(*) AS cnt FROM {table};"
        statement_id = execute_statement(
            client, mode, cluster_id, workgroup_name, database, db_user,
            sql, description=f"COUNT(*) {table}",
        )
        if not statement_id:
            continue

        if not wait_for_statement(client, statement_id, f"COUNT(*) {table}"):
            counts[table] = -1
            continue

        # Fetch result
        try:
            result = client.get_statement_result(Id=statement_id)
            records = result.get("Records", [])
            if records and records[0]:
                counts[table] = int(records[0][0].get("longValue", 0))
            else:
                counts[table] = 0
        except ClientError as e:
            logger.error(f"Failed to get count for {table}: {e}")
            counts[table] = -1

    return counts


# --- Orchestration ---


def seed_all(
    mode: str,
    cluster_id: str,
    workgroup_name: str,
    database: str,
    db_user: str,
    region: str,
    dry_run: bool = False,
    skip_data_load: bool = False,
    truncate_first: bool = True,
) -> None:
    """Orchestrate the full Redshift seeding process.

    Steps:
      1. Create tables (IF NOT EXISTS)
      2. Truncate existing data (optional, for idempotency)
      3. Load CSV data via batched INSERT statements
      4. Verify row counts
    """
    logger.info("=" * 60)
    logger.info("Redshift Seed Script")
    logger.info("=" * 60)
    logger.info(f"  Mode:           {mode}")
    if mode == "cluster":
        logger.info(f"  Cluster ID:     {cluster_id}")
        logger.info(f"  DB User:        {db_user}")
    else:
        logger.info(f"  Workgroup:      {workgroup_name}")
    logger.info(f"  Database:       {database}")
    logger.info(f"  Region:         {region}")
    logger.info(f"  Dry run:        {dry_run}")
    logger.info(f"  Skip load:      {skip_data_load}")
    logger.info(f"  Truncate first: {truncate_first}")
    logger.info(f"  Sample dir:     {SAMPLE_DIR}")
    logger.info("")

    client = None if dry_run else get_redshift_data_client(region)

    # Step 1: Create tables
    logger.info("--- Step 1: Creating tables (IF NOT EXISTS) ---")
    create_statements = [
        (CREATE_CUSTOMERS_SQL, "CREATE TABLE customers"),
        (CREATE_MONTHLY_SALES_SQL, "CREATE TABLE monthly_sales"),
        (CREATE_RISK_ASSESSMENTS_SQL, "CREATE TABLE risk_assessments"),
    ]

    for sql, desc in create_statements:
        success = execute_and_wait(
            client, mode, cluster_id, workgroup_name, database, db_user,
            sql, description=desc, dry_run=dry_run,
        )
        if not success and not dry_run:
            logger.error(f"Failed: {desc} — aborting")
            sys.exit(1)

    # Step 2: Truncate (for idempotent re-runs)
    if truncate_first:
        logger.info("")
        logger.info("--- Step 2: Truncating existing data ---")
        truncate_statements = [
            (TRUNCATE_CUSTOMERS_SQL, "TRUNCATE customers"),
            (TRUNCATE_MONTHLY_SALES_SQL, "TRUNCATE monthly_sales"),
            (TRUNCATE_RISK_ASSESSMENTS_SQL, "TRUNCATE risk_assessments"),
        ]

        for sql, desc in truncate_statements:
            success = execute_and_wait(
                client, mode, cluster_id, workgroup_name, database, db_user,
                sql, description=desc, dry_run=dry_run,
            )
            if not success and not dry_run:
                logger.warning(f"Truncate failed for {desc} — table may be empty, continuing...")

    # Step 3: Load data
    if not skip_data_load:
        logger.info("")
        logger.info("--- Step 3: Loading data ---")

        total_customers = load_customers(
            client, mode, cluster_id, workgroup_name, database, db_user, dry_run
        )
        total_sales = load_monthly_sales(
            client, mode, cluster_id, workgroup_name, database, db_user, dry_run
        )
        total_risk = load_risk_assessments(
            client, mode, cluster_id, workgroup_name, database, db_user, dry_run
        )

    # Step 4: Verify
    if not dry_run and not skip_data_load:
        logger.info("")
        logger.info("--- Step 4: Verifying row counts ---")
        counts = verify_table_counts(
            client, mode, cluster_id, workgroup_name, database, db_user
        )
        for table, count in counts.items():
            status = "OK" if count > 0 else "EMPTY" if count == 0 else "ERROR"
            logger.info(f"  {table}: {count} rows [{status}]")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Seeding complete!")
    logger.info(f"  Database:  {database}")
    logger.info(f"  Tables:    customers, monthly_sales, risk_assessments")
    if not skip_data_load and not dry_run:
        logger.info(f"  Customers: {total_customers} rows")
        logger.info(f"  Sales:     {total_sales} rows")
        logger.info(f"  Risk:      {total_risk} rows")
    logger.info("=" * 60)


def main() -> None:
    """Parse arguments and run the seed process."""
    parser = argparse.ArgumentParser(
        description="Seed Redshift with sample data for the AgentCore MCP demo."
    )
    parser.add_argument(
        "--mode",
        choices=["cluster", "serverless"],
        default=os.environ.get("AGENTCORE_REDSHIFT_MODE", "cluster"),
        help="Connection mode: 'cluster' (provisioned) or 'serverless' (default: cluster)",
    )
    parser.add_argument(
        "--cluster-id",
        default=os.environ.get("AGENTCORE_REDSHIFT_CLUSTER_ID", DEFAULT_CLUSTER_ID),
        help=f"Redshift cluster identifier (default: {DEFAULT_CLUSTER_ID})",
    )
    parser.add_argument(
        "--workgroup-name",
        default=os.environ.get("AGENTCORE_REDSHIFT_WORKGROUP", DEFAULT_WORKGROUP_NAME),
        help=f"Redshift Serverless workgroup name (default: {DEFAULT_WORKGROUP_NAME})",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("AGENTCORE_REDSHIFT_DATABASE", DEFAULT_DATABASE),
        help=f"Target database name (default: {DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "--db-user",
        default=os.environ.get("AGENTCORE_REDSHIFT_DB_USER", DEFAULT_DB_USER),
        help=f"Database user for cluster mode IAM auth (default: {DEFAULT_DB_USER})",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AGENTCORE_REGION", DEFAULT_REGION),
        help=f"AWS region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview SQL statements without executing against Redshift.",
    )
    parser.add_argument(
        "--skip-data-load",
        action="store_true",
        help="Create tables but skip loading data.",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Skip truncating tables before loading (may cause duplicate key errors).",
    )
    args = parser.parse_args()

    seed_all(
        mode=args.mode,
        cluster_id=args.cluster_id,
        workgroup_name=args.workgroup_name,
        database=args.database,
        db_user=args.db_user,
        region=args.region,
        dry_run=args.dry_run,
        skip_data_load=args.skip_data_load,
        truncate_first=not args.no_truncate,
    )


if __name__ == "__main__":
    main()
