"""
Glue ETL Job: CSV to Parquet transformation.

Reads a CSV file from the source S3 bucket and writes it as Parquet
to the target S3 bucket.

Parameters:
  --source_bucket: S3 bucket containing the input CSV
  --source_key: Object key of the uploaded CSV file
  --target_bucket: S3 bucket for Parquet output
"""
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext

args = getResolvedOptions(sys.argv, ["source_bucket", "source_key", "target_bucket"])

sc = SparkContext()
glueContext = GlueContext(sc)

# Read CSV from source
input_path = f"s3://{args['source_bucket']}/{args['source_key']}"
print(f"Reading CSV from: {input_path}")

df = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [input_path]},
    format="csv",
    format_options={"withHeader": True},
)

print(f"Record count: {df.count()}")

# Write as Parquet to target
# Strip prefix and extension to build output path
output_key = args["source_key"].replace("input/", "").replace(".csv", "")
output_path = f"s3://{args['target_bucket']}/output/{output_key}"
print(f"Writing Parquet to: {output_path}")

glueContext.write_dynamic_frame.from_options(
    frame=df,
    connection_type="s3",
    connection_options={"path": output_path},
    format="parquet",
)

print(f"Successfully transformed {input_path} → {output_path}")
