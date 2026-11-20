"""Glue ETL Job: Bronze to Silver transformation.

Reads raw CSV data from the landing zone (cataloged by Glue Crawler),
deduplicates by transaction_id + customer_id, adds metadata columns,
and writes partitioned Parquet to the silver tier.
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_timestamp, lit
from pyspark.sql.window import Window
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "source_database",
    "source_table",
    "target_path",
    "partition_key",
    "execution_date",
    "dedup_keys",
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Read from Glue catalog
datasource = glueContext.create_dynamic_frame.from_catalog(
    database=args["source_database"],
    table_name=args["source_table"],
)

# Convert to Spark DataFrame for transformations
df = datasource.toDF()

print(f"Input rows: {df.count()}")
print(f"Input schema: {df.columns}")

# Deduplicate by specified keys
dedup_keys = args["dedup_keys"].split(",")
window = Window.partitionBy(*dedup_keys).orderBy(col("date").desc())
df_deduped = df.withColumn("_row_num", F.row_number().over(window)) \
    .filter(col("_row_num") == 1) \
    .drop("_row_num")

# Add metadata columns
df_enriched = df_deduped \
    .withColumn("ingested_at", current_timestamp()) \
    .withColumn("source_layer", lit("bronze")) \
    .withColumn("dt", lit(args["execution_date"]))

print(f"Output rows after dedup: {df_enriched.count()}")

# Write partitioned Parquet to silver tier
df_enriched.write \
    .mode("overwrite") \
    .partitionBy(args["partition_key"]) \
    .parquet(args["target_path"])

print(f"Written to: {args['target_path']}")

job.commit()
