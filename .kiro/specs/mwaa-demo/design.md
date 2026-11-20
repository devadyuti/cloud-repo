# Design: MWAA Serverless Demo

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Account (eu-west-1)                       │
│                                                                       │
│  ┌──────────────┐     ┌──────────────────────────────────────────┐  │
│  │ GitHub Actions│────▶│ S3 Bucket (any-company-mwaa-demo-dags-{acct}) │  │
│  │   CI/CD      │     │  ├── dags/                                │  │
│  └──────────────┘     │  ├── plugins/                             │  │
│         │ OIDC        │  └── requirements.txt                     │  │
│         ▼             └───────────────┬──────────────────────────┘  │
│  ┌──────────────┐                     │ auto-sync                    │
│  │  IAM Role    │                     ▼                              │
│  └──────────────┘     ┌──────────────────────────────────────────┐  │
│                       │     MWAA Serverless (any-company-mwaa-demo)    │  │
│                       │     ┌────────┐ ┌────────┐ ┌────────┐     │  │
│                       │     │hello   │ │etl     │ │ecs     │     │  │
│                       │     │_world  │ │pipeline│ │_exec   │     │  │
│                       │     └────────┘ └───┬────┘ └───┬────┘     │  │
│                       └────────────────────┼──────────┼──────────┘  │
│                                            │          │              │
│              ┌─────────────────────────────┼──────────┼───────┐     │
│              │            VPC              │          │       │     │
│              │  ┌─────────┐  ┌─────────┐  │          │       │     │
│              │  │Private  │  │Private  │  │          │       │     │
│              │  │Subnet-a │  │Subnet-b │  │          │       │     │
│              │  └─────────┘  └─────────┘  │          │       │     │
│              │  ┌─────────┐  ┌─────────┐  │          │       │     │
│              │  │Public   │  │Public   │  │          │       │     │
│              │  │Subnet-a │  │Subnet-b │  │          │       │     │
│              │  └─────────┘  └─────────┘  │          │       │     │
│              │       │                    │          │       │     │
│              │  ┌────┴────┐               │          │       │     │
│              │  │NAT GW   │               │          │       │     │
│              │  └─────────┘               │          │       │     │
│              └────────────────────────────┼──────────┼───────┘     │
│                                           │          │              │
│         ┌─────────────────────────────────┘          │              │
│         ▼                                            ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  AWS Glue    │  │  Redshift    │  │  ECS Fargate             │  │
│  │  (transform) │  │  Serverless  │  │  (any-company-demo-cluster)   │  │
│  └──────────────┘  │  (or mock)   │  │  ┌────────────────────┐  │  │
│                    └──────────────┘  │  │ ETL Container      │  │  │
│                                      │  │ (ECR image)        │  │  │
│  ┌──────────────┐                    │  └────────────────────┘  │  │
│  │ Lambda       │───REST API────────▶│                          │  │
│  │ (dag-trigger)│                    └──────────────────────────┘  │
│  └──────────────┘                                                    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ CloudWatch Dashboard                                          │   │
│  │ [QueuedTasks] [RunningTasks] [Heartbeat] [Failures]           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Stack Design

The CDK app is split into 5 stacks with explicit dependencies:

| Stack | Resources | Dependencies |
|-------|-----------|--------------|
| `MwaaVpcStack` | Lookup existing VPC/subnets, create MWAA SG | None (requires `vpc_id` in CDK context) |
| `MwaaStack` | S3 bucket, MWAA environment, execution role | VpcStack |
| `MwaaEcsStack` | ECS cluster, task definition, ECR repo | VpcStack |
| `MwaaLambdaStack` | Lambda function, IAM role | MwaaStack |
| `MwaaMonitoringStack` | CloudWatch dashboard | MwaaStack |

## Key Design Decisions

### 1. MWAA Serverless vs Classic
Using MWAA Serverless (not Classic) because:
- No capacity planning needed
- Scales to zero when idle (cost demo-friendly)
- Simpler configuration (no environment class, min/max workers)

### 2. Existing VPC Lookup
Using `Vpc.from_lookup()` to reference an existing VPC in the account rather than creating a new one (VPC quota constraint). The VPC ID is passed via CDK context (`-c vpc_id=vpc-xxx`). The existing VPC must have private subnets with NAT/egress and the necessary VPC endpoints already provisioned.

### 3. Public Web Server
Web server access set to PUBLIC for demo ease. Production should use PRIVATE with VPN/PrivateLink access.

### 4. Redshift Mock Fallback
Redshift Serverless can take 10+ minutes to provision. The ETL DAG includes a fallback PythonOperator that logs "Redshift load simulated" if Redshift is unavailable.

### 5. GitHub OIDC for CI/CD
No static AWS credentials stored in GitHub. The workflow assumes an IAM role via OIDC federation.

## File Structure

```
mwaa-serverless-demo/
├── app.py                          # CDK entry point
├── cdk.json
├── requirements-cdk.txt            # CDK dependencies
├── stacks/
│   ├── __init__.py
│   ├── vpc_stack.py
│   ├── mwaa_stack.py
│   ├── ecs_stack.py
│   ├── lambda_stack.py
│   └── monitoring_stack.py
├── dags/
│   ├── hello_world.py
│   ├── sample_etl_pipeline.py
│   ├── container_execution.py
│   └── api_triggered.py
├── plugins/                        # Empty (extensibility placeholder)
├── requirements.txt                # Airflow provider dependencies
├── tests/
│   ├── conftest.py
│   └── test_dags.py
├── docker/
│   ├── Dockerfile
│   └── app/
│       └── pipeline.py
├── lambda/
│   └── trigger_dag.py
├── .github/
│   └── workflows/
│       └── deploy-dags.yml
└── README.md
```

## Interface Contracts

### Lambda → MWAA REST API
```
POST /dags/{dag_id}/dagRuns
Headers: Authorization: Bearer {web_login_token}
Body: {"conf": {"source": "lambda", "date": "2026-07-28"}}
```

### GitHub Actions → S3
```
aws s3 sync dags/ s3://{bucket}/dags/ --delete
aws s3 cp requirements.txt s3://{bucket}/requirements.txt
```

### MWAA → ECS
```
EcsRunTaskOperator(
    cluster="any-company-demo-cluster",
    task_definition="any-company-etl-task",
    launch_type="FARGATE",
    network_configuration={subnets, security_groups}
)
```
