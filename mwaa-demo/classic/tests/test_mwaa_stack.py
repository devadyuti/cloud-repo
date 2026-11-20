"""Unit tests for MwaaStack."""

import aws_cdk as cdk
from aws_cdk import assertions
from aws_cdk import aws_ec2 as ec2

from stacks.vpc_stack import VpcStack
from stacks.mwaa_stack import MwaaStack


class TestMwaaStack:
    """Tests for the MWAA stack."""

    def _create_stack(self):
        """Helper to create a VPC + MWAA stack pair for testing."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        env = cdk.Environment(account="123456789012", region="eu-west-1")
        vpc_stack = VpcStack(app, "TestVpcStack", env=env)
        mwaa_stack = MwaaStack(
            app,
            "TestMwaaStack",
            vpc=vpc_stack.vpc,
            mwaa_sg=vpc_stack.mwaa_sg,
            env=env,
        )
        return mwaa_stack

    def test_s3_bucket_created(self):
        """MwaaStack creates a versioned S3 bucket with public access blocked."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::S3::Bucket", {
            "VersioningConfiguration": {"Status": "Enabled"},
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        })

    def test_execution_role_created(self):
        """MwaaStack creates an IAM role with Airflow service principals."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Role", {
            "AssumeRolePolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Principal": {"Service": "airflow-env.amazonaws.com"},
                        "Effect": "Allow",
                    }),
                    assertions.Match.object_like({
                        "Principal": {"Service": "airflow.amazonaws.com"},
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_s3_policy_includes_public_access_block_actions(self):
        """S3 bucket policy includes GetBucketPublicAccessBlock and GetAccountPublicAccessBlock."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "S3BucketAccess",
                        "Action": assertions.Match.array_with([
                            "s3:GetBucketPublicAccessBlock",
                            "s3:GetAccountPublicAccessBlock",
                        ]),
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_s3_policy_includes_wildcard_resource(self):
        """S3 bucket policy includes wildcard resource for account-level S3 actions."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "S3BucketAccess",
                        "Resource": assertions.Match.array_with(["*"]),
                    }),
                ]),
            },
        })

    def test_glue_access_policy(self):
        """Execution role has Glue access for StartJobRun and GetJobRun."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "GlueAccess",
                        "Action": ["glue:StartJobRun", "glue:GetJobRun"],
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_kms_access_policy(self):
        """Execution role has KMS permissions for SQS Celery broker encryption."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "KmsAccess",
                        "Action": [
                            "kms:Decrypt",
                            "kms:Encrypt",
                            "kms:GenerateDataKey",
                            "kms:DescribeKey",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                    }),
                ]),
            },
        })

    def test_ecs_access_policy(self):
        """Execution role has ECS RunTask and PassRole permissions."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "EcsAccess",
                        "Action": [
                            "ecs:RunTask",
                            "ecs:DescribeTasks",
                            "iam:PassRole",
                        ],
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_mwaa_environment_created(self):
        """MwaaStack creates the MWAA environment with correct name and DAG path."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::MWAA::Environment", {
            "Name": "any-company-mwaa-demo",
            "DagS3Path": "dags/",
            "WebserverAccessMode": "PUBLIC_ONLY",
        })

    def test_mwaa_airflow_version(self):
        """MwaaStack deploys Airflow 3.2.1."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::MWAA::Environment", {
            "AirflowVersion": "3.2.1",
        })

    def test_mwaa_environment_network_config(self):
        """MWAA environment has network configuration with security group."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::MWAA::Environment", {
            "NetworkConfiguration": assertions.Match.object_like({
                "SecurityGroupIds": assertions.Match.any_value(),
                "SubnetIds": assertions.Match.any_value(),
            }),
        })

    def test_environment_name_property(self):
        """MwaaStack exposes environment_name property."""
        stack = self._create_stack()
        assert stack.environment_name == "any-company-mwaa-demo"

    def test_dags_bucket_property(self):
        """MwaaStack exposes dags_bucket property returning the S3 bucket."""
        stack = self._create_stack()
        bucket = stack.dags_bucket
        assert bucket is not None
        assert bucket.bucket_name is not None

    def test_initial_bucket_content_deployment(self):
        """MwaaStack deploys a single BucketDeployment with dags/, plugins/, and requirements.txt."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        # Consolidated into one BucketDeployment custom resource
        template.resource_count_is("Custom::CDKBucketDeployment", 1)

    def test_mwaa_startup_script_s3_path(self):
        """MWAA environment runs startup.sh (installs dbt Core into an isolated venv)."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::MWAA::Environment", {
            "StartupScriptS3Path": "startup.sh",
        })

    def test_startup_script_installs_dbt_in_venv(self):
        """startup.sh builds a dedicated dbt venv and skips the webserver."""
        from stacks.mwaa_stack import PROJECT_ROOT

        script = (PROJECT_ROOT / "startup.sh").read_text()
        assert "python3 -m venv" in script
        assert "dbt-redshift==" in script
        assert 'MWAA_AIRFLOW_COMPONENT}" != "webserver"' in script

    def test_mwaa_requirements_s3_path(self):
        """MWAA environment references requirements.txt in S3."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::MWAA::Environment", {
            "RequirementsS3Path": "requirements.txt",
        })
