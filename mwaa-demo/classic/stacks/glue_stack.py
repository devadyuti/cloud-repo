"""Glue Stack — Crawler, ETL Job, and Athena database for the data lake pipeline."""

from aws_cdk import (
    Aws,
    RemovalPolicy,
    Stack,
    aws_athena as athena,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct


class GlueStack(Stack):
    """Creates Glue Crawler, ETL Job, Athena workgroup and database for the data lake ETL DAG."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        dags_bucket_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dags_bucket = s3.Bucket.from_bucket_name(
            self, "DagsBucket", dags_bucket_name
        )

        # --- IAM Role for Glue ---
        glue_role = iam.Role(
            self,
            "GlueCrawlerRole",
            role_name="GlueCrawlerRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
            ],
        )

        # Glue needs S3 access to the data lake bucket
        glue_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3DataLakeAccess",
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:DeleteObject",
                ],
                resources=[
                    dags_bucket.bucket_arn,
                    f"{dags_bucket.bucket_arn}/*",
                ],
            )
        )

        # --- Glue Database ---
        self._database = glue.CfnDatabase(
            self,
            "DataLakeDatabase",
            catalog_id=Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="anycompany_data_lake",
                description="Data lake database for MWAA demo — bronze/silver/gold tiers",
            ),
        )

        # --- Glue Crawler ---
        self._crawler = glue.CfnCrawler(
            self,
            "TransactionsCrawler",
            name="any-company-transactions-crawler",
            role=glue_role.role_arn,
            database_name="anycompany_data_lake",
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{dags_bucket_name}/landing/transactions/",
                    ),
                ],
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE",
                delete_behavior="LOG",
            ),
            table_prefix="raw_",
        )
        self._crawler.add_dependency(self._database)

        # --- Upload Glue ETL Script to S3 ---
        s3deploy.BucketDeployment(
            self,
            "GlueScriptDeploy",
            sources=[s3deploy.Source.asset("glue-scripts/")],
            destination_bucket=dags_bucket,
            destination_key_prefix="glue-scripts/",
            prune=False,
        )

        # --- Glue ETL Job ---
        self._etl_job = glue.CfnJob(
            self,
            "BronzeToSilverJob",
            name="any-company-bronze-to-silver",
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=f"s3://{dags_bucket_name}/glue-scripts/bronze_to_silver.py",
            ),
            default_arguments={
                "--job-language": "python",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--source_database": "anycompany_data_lake",
                "--source_table": "raw_transactions",
                "--target_path": f"s3://{dags_bucket_name}/silver/transactions/",
                "--TempDir": f"s3://{dags_bucket_name}/glue-temp/",
            },
            glue_version="4.0",
            number_of_workers=2,
            worker_type="G.1X",
            timeout=30,  # minutes
        )

        # --- Athena Workgroup ---
        self._workgroup = athena.CfnWorkGroup(
            self,
            "DemoWorkgroup",
            name="mwaa-demo",
            state="ENABLED",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{dags_bucket_name}/athena-results/",
                ),
                enforce_work_group_configuration=False,
            ),
        )

    @property
    def database_name(self) -> str:
        """The Glue database name."""
        return "anycompany_data_lake"

    @property
    def crawler_name(self) -> str:
        """The Glue Crawler name."""
        return "any-company-transactions-crawler"

    @property
    def etl_job_name(self) -> str:
        """The Glue ETL job name."""
        return "any-company-bronze-to-silver"
