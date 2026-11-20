"""Tests for the Glue staging job scripts' Data Catalog source configuration.

These scripts (`stage_sales_data.py`, `stage_customer_data.py`) run inside the
AWS Glue runtime and import `awsglue`/`pyspark` and call `SparkContext()` at
module load time, so they cannot be imported directly here. Instead we parse the
source statically to assert the catalog database/table each job reads from.

The important invariant these tests guard: the `table_name` a job reads must
match the table the Glue crawler actually creates. The RawCrawler in
`templates/stream-0-data-lake.yaml` sets TablePrefix 'raw_', so it names each
table with a 'raw_' prefix on the S3 source folder -- `s3://.../sales/` ->
table `raw_sales`, `s3://.../customers/` -> table `raw_customers`. Reading a
table name that does not exist in the catalog makes the job fail at
`create_dynamic_frame.from_catalog`.
"""

import ast
import pathlib

SCRIPTS_DIR = pathlib.Path(__file__).parent


def _assignments(script_name):
    """Return a dict of top-level `name = <str literal>` assignments in a script."""
    source = (SCRIPTS_DIR / script_name).read_text()
    tree = ast.parse(source)
    values = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value.value, str):
                    values[target.id] = node.value.value
    return values


def test_sales_job_reads_raw_sales_table():
    values = _assignments("stage_sales_data.py")
    assert values["db_name"] == "raw"
    # Must match the crawler-produced table for the s3://.../sales/ folder
    # (TablePrefix 'raw_' + folder name 'sales').
    assert values["tbl_name"] == "raw_sales"


def test_sales_job_output_prefix_matches_source_folder():
    values = _assignments("stage_sales_data.py")
    # The S3 output folder stays the bare source-folder name (no 'raw_'); only
    # the Glue catalog table name carries the crawler's 'raw_' TablePrefix.
    assert values["PREFIX"] == "sales"


def test_customer_job_reads_raw_customers_table():
    values = _assignments("stage_customer_data.py")
    assert values["db_name"] == "raw"
    # Must match the crawler-produced table for the s3://.../customers/ folder
    # (TablePrefix 'raw_' + folder name 'customers').
    assert values["tbl_name"] == "raw_customers"


def test_staging_jobs_share_naming_convention():
    """Both jobs read from the 'raw' database using the crawler-produced table
    name: TablePrefix 'raw_' + source-folder name."""
    expected = {
        "stage_sales_data.py": "raw_sales",
        "stage_customer_data.py": "raw_customers",
    }
    for script, table in expected.items():
        values = _assignments(script)
        assert values["db_name"] == "raw"
        assert values["tbl_name"].startswith("raw_"), (
            f"{script} reads '{values['tbl_name']}', but the crawler sets "
            "TablePrefix 'raw_' so every raw table name carries a 'raw_' prefix"
        )
        assert values["tbl_name"] == table
