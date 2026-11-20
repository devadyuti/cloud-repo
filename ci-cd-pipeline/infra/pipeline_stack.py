"""CDK Stack — CI/CD pipeline infrastructure for the Demo Orders API.

Creates:
- S3 artifact bucket
- CodeBuild project (runs tests + SAM build/package)
- CodePipeline V2 (Source → Build → Deploy)
- IAM roles for CodePipeline, CodeBuild, and CloudFormation

NOTE: The CodeCommit repository (demo-orders-api) already exists.
This stack references it by name — it does NOT create it.

The SAM template uses AutoPublishAlias + DeploymentPreference which causes
CloudFormation to automatically create a CodeDeploy deployment during the
Deploy stage. No separate CodeDeploy action is needed in the pipeline.
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
    aws_iam as iam,
)
from constructs import Construct


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ─── S3 Artifact Bucket ───────────────────────────────────────────
        artifact_bucket = s3.Bucket(
            self,
            "ArtifactBucket",
            bucket_name=f"demo-pipeline-artifacts-dev-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # ─── Reference Existing CodeCommit Repository ─────────────────────
        repo = codecommit.Repository.from_repository_name(
            self,
            "OrdersApiRepo",
            repository_name="aws-architecture-analysis",
        )

        # ─── CloudFormation Execution Role ────────────────────────────────
        cfn_role = iam.Role(
            self,
            "CloudFormationRole",
            assumed_by=iam.ServicePrincipal("cloudformation.amazonaws.com"),
            description="Role assumed by CloudFormation to deploy the Orders API stack",
        )
        cfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:*",
                    "apigateway:*",
                    "codedeploy:*",
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:PutMetricAlarm",
                    "cloudwatch:DeleteAlarms",
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",
                    "iam:GetRole",
                    "iam:PassRole",
                    "iam:TagRole",
                    "iam:UntagRole",
                    "cloudformation:CreateChangeSet",
                    "s3:GetObject",
                ],
                resources=["*"],
            )
        )

        # ─── CodeBuild Project ────────────────────────────────────────────
        build_project = codebuild.PipelineProject(
            self,
            "OrdersApiBuild",
            project_name="demo-orders-api-build",
            description="Runs tests and SAM build/package for Demo Orders API",
            build_spec=codebuild.BuildSpec.from_source_filename(
                "ci-cd-pipeline/buildspec.yml"
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                compute_type=codebuild.ComputeType.SMALL,
            ),
            environment_variables={
                "ARTIFACT_BUCKET": codebuild.BuildEnvironmentVariable(
                    value=artifact_bucket.bucket_name
                ),
            },
        )

        # Grant CodeBuild access to the artifact bucket and CodeCommit
        artifact_bucket.grant_read_write(build_project)
        repo.grant_pull(build_project)

        # ─── CodePipeline V2 ─────────────────────────────────────────────
        source_output = codepipeline.Artifact("SourceOutput")
        build_output = codepipeline.Artifact("BuildOutput")

        pipeline = codepipeline.Pipeline(
            self,
            "OrdersApiPipeline",
            pipeline_name="demo-orders-api-pipeline",
            pipeline_type=codepipeline.PipelineType.V2,
            artifact_bucket=artifact_bucket,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        actions.CodeCommitSourceAction(
                            action_name="CodeCommit_Source",
                            repository=repo,
                            branch="main",
                            output=source_output,
                            trigger=actions.CodeCommitTrigger.EVENTS,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[
                        actions.CodeBuildAction(
                            action_name="CodeBuild_Build",
                            project=build_project,
                            input=source_output,
                            outputs=[build_output],
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[
                        actions.CloudFormationCreateUpdateStackAction(
                            action_name="CloudFormation_Deploy",
                            stack_name="demo-orders-api-stack",
                            template_path=build_output.at_path("packaged.yaml"),
                            admin_permissions=False,
                            deployment_role=cfn_role,
                            cfn_capabilities=[
                                cdk.CfnCapabilities.NAMED_IAM,
                                cdk.CfnCapabilities.AUTO_EXPAND,
                            ],
                        )
                    ],
                ),
            ],
        )

        # ─── Outputs ─────────────────────────────────────────────────────
        CfnOutput(self, "PipelineName", value=pipeline.pipeline_name)
        CfnOutput(self, "ArtifactBucketName", value=artifact_bucket.bucket_name)
