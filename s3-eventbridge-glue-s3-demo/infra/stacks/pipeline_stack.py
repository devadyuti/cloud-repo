"""
CDK Stack: S3 → EventBridge (Rule + Scheduler) → Glue ETL Pipeline

Two trigger patterns:
1. Event-driven: S3 PutObject → EventBridge Rule → Lambda → Glue StartJobRun
2. Scheduled: EventBridge Scheduler → Glue StartJobRun directly (no Lambda)

Creates:
- Source S3 bucket with EventBridge notifications enabled
- Target S3 bucket for Parquet output
- Glue job (Spark, Glue 5.0) with the ETL script
- Lambda function that starts the Glue job (EventBridge rule target)
- EventBridge rule matching CSV uploads to input/ prefix
- EventBridge Scheduler (daily 8am Europe/London) calling Glue directly
- DLQ (SQS) for failed EventBridge deliveries
- IAM roles for Glue, Lambda, and Scheduler
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_iam as iam,
    aws_glue as glue,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_scheduler as scheduler,
    CfnOutput,
)
from constructs import Construct


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env_suffix = "dev"

        # ──────────────────────────────────────────────
        # S3 Buckets
        # ──────────────────────────────────────────────
        source_bucket = s3.Bucket(
            self,
            "SourceBucket",
            bucket_name=f"demo-source-{env_suffix}-{self.account}",
            event_bridge_enabled=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        target_bucket = s3.Bucket(
            self,
            "TargetBucket",
            bucket_name=f"demo-target-{env_suffix}-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ──────────────────────────────────────────────
        # Glue IAM Role
        # ──────────────────────────────────────────────
        glue_role = iam.Role(
            self,
            "GlueETLRole",
            role_name=f"glue-etl-role-{env_suffix}",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
            ],
        )

        source_bucket.grant_read(glue_role)
        target_bucket.grant_write(glue_role)

        # ──────────────────────────────────────────────
        # Upload Glue script to source bucket (scripts/ prefix)
        # ──────────────────────────────────────────────
        script_deployment = s3deploy.BucketDeployment(
            self,
            "GlueScriptDeployment",
            sources=[s3deploy.Source.asset("../glue")],
            destination_bucket=source_bucket,
            destination_key_prefix="scripts",
        )

        # ──────────────────────────────────────────────
        # Glue Job
        # ──────────────────────────────────────────────
        glue_job_name = "csv-to-parquet-job"

        glue_job = glue.CfnJob(
            self,
            "CsvToParquetJob",
            name=glue_job_name,
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                script_location=f"s3://{source_bucket.bucket_name}/scripts/csv_to_parquet.py",
                python_version="3",
            ),
            glue_version="5.0",
            number_of_workers=2,
            worker_type="G.1X",
            timeout=5,  # minutes
            default_arguments={
                "--source_bucket": source_bucket.bucket_name,
                "--source_key": "placeholder",
                "--target_bucket": target_bucket.bucket_name,
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
            },
        )

        glue_job.node.add_dependency(script_deployment)

        # ──────────────────────────────────────────────
        # DLQ for EventBridge failed deliveries
        # ──────────────────────────────────────────────
        dlq = sqs.Queue(
            self,
            "EventBridgeDLQ",
            queue_name=f"demo-eventbridge-dlq-{env_suffix}",
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ──────────────────────────────────────────────
        # Lambda function to start Glue job
        # (EventBridge → Lambda → Glue StartJobRun)
        # ──────────────────────────────────────────────
        start_glue_fn = _lambda.Function(
            self,
            "StartGlueJobFn",
            function_name=f"start-glue-etl-{env_suffix}",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            timeout=Duration.seconds(30),
            environment={
                "GLUE_JOB_NAME": glue_job_name,
                "TARGET_BUCKET": target_bucket.bucket_name,
            },
            code=_lambda.Code.from_inline(
                """
import json
import os
import boto3

glue = boto3.client("glue")

def handler(event, context):
    \"\"\"Start Glue job with source bucket/key from S3 EventBridge event.\"\"\"
    print(json.dumps(event))

    detail = event.get("detail", {})
    source_bucket = detail.get("bucket", {}).get("name")
    source_key = detail.get("object", {}).get("key")

    if not source_bucket or not source_key:
        raise ValueError(f"Missing bucket or key in event detail: {detail}")

    # Only process files under input/ prefix
    if not source_key.startswith("input/"):
        print(f"Skipping key not in input/ prefix: {source_key}")
        return {"statusCode": 200, "body": "Skipped - not in input/ prefix"}

    job_name = os.environ["GLUE_JOB_NAME"]
    target_bucket = os.environ["TARGET_BUCKET"]

    print(f"Starting Glue job '{job_name}' for s3://{source_bucket}/{source_key}")

    response = glue.start_job_run(
        JobName=job_name,
        Arguments={
            "--source_bucket": source_bucket,
            "--source_key": source_key,
            "--target_bucket": target_bucket,
        },
    )

    run_id = response["JobRunId"]
    print(f"Glue job run started: {run_id}")

    return {"statusCode": 200, "body": json.dumps({"jobRunId": run_id})}
"""
            ),
        )

        # Grant Lambda permission to start the Glue job
        start_glue_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["glue:StartJobRun"],
                resources=[
                    f"arn:aws:glue:{self.region}:{self.account}:job/{glue_job_name}"
                ],
            )
        )

        # ──────────────────────────────────────────────
        # EventBridge Rule
        # ──────────────────────────────────────────────
        rule = events.Rule(
            self,
            "S3CsvUploadRule",
            rule_name="s3-csv-upload-rule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [source_bucket.bucket_name]},
                    "object": {"key": [{"prefix": "input/"}, {"suffix": ".csv"}]},
                },
            ),
        )

        # Target: Lambda function with DLQ and retry
        rule.add_target(
            targets.LambdaFunction(
                start_glue_fn,
                dead_letter_queue=dlq,
                retry_attempts=2,
                max_event_age=Duration.seconds(300),
            )
        )

        # ──────────────────────────────────────────────
        # Pattern 2: EventBridge Scheduler
        # Daily at 8am Europe/London → Glue StartJobRun directly
        # ──────────────────────────────────────────────
        scheduler_role = iam.Role(
            self,
            "SchedulerGlueRole",
            role_name=f"scheduler-glue-role-{env_suffix}",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )

        scheduler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["glue:StartJobRun"],
                resources=[
                    f"arn:aws:glue:{self.region}:{self.account}:job/{glue_job_name}"
                ],
            )
        )

        daily_schedule = scheduler.CfnSchedule(
            self,
            "DailyGlueEtlSchedule",
            name="daily-glue-etl-schedule",
            schedule_expression="cron(0 8 * * ? *)",
            schedule_expression_timezone="Europe/London",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE",
                maximum_window_in_minutes=15,
            ),
            state="ENABLED",
            target=scheduler.CfnSchedule.TargetProperty(
                arn="arn:aws:scheduler:::aws-sdk:glue:startJobRun",
                role_arn=scheduler_role.role_arn,
                input='{"JobName": "'
                + glue_job_name
                + '", "Arguments": {"--source_bucket": "'
                + source_bucket.bucket_name
                + '", "--source_key": "input/daily-feed.csv", "--target_bucket": "'
                + target_bucket.bucket_name
                + '"}}',
            ),
        )

        # ──────────────────────────────────────────────
        # Outputs
        # ──────────────────────────────────────────────
        CfnOutput(self, "SourceBucketName", value=source_bucket.bucket_name)
        CfnOutput(self, "TargetBucketName", value=target_bucket.bucket_name)
        CfnOutput(self, "GlueJobName", value=glue_job_name)
        CfnOutput(self, "LambdaFunctionName", value=start_glue_fn.function_name)
        CfnOutput(self, "EventBridgeRuleName", value=rule.rule_name)
        CfnOutput(self, "SchedulerName", value="daily-glue-etl-schedule")
        CfnOutput(self, "DLQUrl", value=dlq.queue_url)
