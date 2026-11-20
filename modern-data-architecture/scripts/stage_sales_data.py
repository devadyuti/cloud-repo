#MIT No Attribution
#
#Copyright 2023 Amazon.com, Inc. or its affiliates.
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of this
#software and associated documentation files (the "Software"), to deal in the Software
#without restriction, including without limitation the rights to use, copy, modify,
#merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#permit persons to whom the Software is furnished to do so.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import pyspark.sql.functions as f
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'output_s3_bucket_name'])

sc = SparkContext()
glueContext = GlueContext(sc)
logger = glueContext.get_logger()

job_name = args['JOB_NAME']
job_run_id = args['JOB_RUN_ID']
logger.info("Initiating Job: " + job_name + '-' + job_run_id)

BUCKET_NAME = args['output_s3_bucket_name']
PREFIX = 'sales'

# Data Catalog: database and table name
db_name = "raw"
tbl_name = "raw_sales"

# S3 location for output
output_s3_path = "s3://" + BUCKET_NAME + "/" + PREFIX
logger.info("" + job_name + '-' + job_run_id + " - Output Path:" + output_s3_path)

spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

datasource0 = glueContext.create_dynamic_frame.from_catalog(
    database=db_name, table_name=tbl_name, transformation_ctx="datasource0")

applymapping1 = ApplyMapping.apply(
    frame=datasource0,
    mappings=[
        ("card_id", "long", "card_id", "long"),
        ("customer_id", "long", "customer_id", "long"),
        ("price", "string", "price", "string"),
        ("product_id", "long", "product_id", "long"),
        ("timestamp", "string", "timestamp", "timestamp"),
    ],
    transformation_ctx="applymapping1")

resolvechoice2 = ResolveChoice.apply(
    frame=applymapping1, choice="make_struct", transformation_ctx="resolvechoice2")

dropnullfields3 = DropNullFields.apply(
    frame=resolvechoice2, transformation_ctx="dropnullfields3")

dataframe = dropnullfields3.toDF()

# 'timestamp' is already a timestamp type (cast in ApplyMapping), so extract the
# partition columns directly. Do NOT re-parse it with to_timestamp(fmt) -- that
# forces a stringify/re-parse against a format and returns null, which dumps every
# row into __HIVE_DEFAULT_PARTITION__.
dataframe2 = dataframe.withColumn('year', f.year(f.col('timestamp')))
dataframe3 = dataframe2.withColumn('month', f.month(f.col('timestamp')))
dataframe4 = dataframe3.withColumn('day', f.dayofmonth(f.col('timestamp')))

# udf returns the value by removing the currency char (null-safe)
@udf(returnType=StringType())
def remove_currency(price):
    if price is None:
        return None
    price = price.replace("$", "")
    return price

dataframe5 = dataframe4.withColumn("price", remove_currency(dataframe4["price"]))

dynframe = DynamicFrame.fromDF(dataframe5, glueContext, "dynframe")

glueContext.purge_s3_path(output_s3_path, {"retentionPeriod": 0})

datasink4 = glueContext.write_dynamic_frame.from_options(
    frame=dynframe,
    connection_type="s3",
    connection_options={"path": output_s3_path, "partitionKeys": ["year", "month", "day"]},
    format="parquet",
    transformation_ctx="datasink4")

job.commit()
logger.info("Job Complete: " + job_name + '-' + job_run_id)
