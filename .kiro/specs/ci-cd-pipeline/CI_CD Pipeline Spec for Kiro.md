# Demo: CI/CD Pipeline for Serverless API

## Overview

A fully automated CI/CD pipeline that deploys a simple REST API (API Gateway + Lambda) using AWS CodeCommit, CodeBuild, CodeDeploy, and CodePipeline.

## Architecture

```
┌────────────┐     push     ┌──────────────┐     build      ┌──────────────┐     deploy     ┌──────────────┐
│ CodeCommit │ ──────────▶  │ CodePipeline │ ────────────▶   │  CodeBuild   │ ────────────▶  │  CodeDeploy  │
│  (source)  │              │ (orchestrate)│                 │(test+package)│                │(traffic shift)│
└────────────┘              └──────────────┘                 └──────────────┘                └──────┬───────┘
                                                                                                    │
                                                                                                    ▼
                                                                                            ┌───────────────┐
                                                                                            │ API Gateway + │
                                                                                            │ Lambda (alias)│
                                                                                            └───────────────┘
```

## What Gets Built

A simple **Order API** with two endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/orders` | Returns list of sample orders |
| POST | `/orders` | Creates a new order (mock) |

## Project Structure

```
repo/
├── src/
│   └── handler.py          # Lambda function code
├── tests/
│   └── test_handler.py     # Unit tests
├── template.yaml           # SAM/CloudFormation template
├── buildspec.yml           # CodeBuild instructions
└── README.md
```

## Requirements

### Functional

1. Code pushed to `main` branch triggers the pipeline automatically
2. CodeBuild runs unit tests — pipeline stops on failure
3. CodeBuild packages the Lambda using SAM
4. Pipeline deploys via CloudFormation changeset (create + execute)
5. API Gateway endpoint is available after successful deployment

### Non-Functional

- Region: `eu-west-1`
- Runtime: Python 3.12
- Lambda memory: 128 MB
- Lambda timeout: 30s
- Pipeline should complete in < 5 minutes

---

## File Contents

### `src/handler.py`

```python
import json
from datetime import datetime

ORDERS = [
    {"id": "ORD-001", "customer": "Acme Corp", "product": "Widget A", "status": "shipped"},
    {"id": "ORD-002", "customer": "Beta Ltd", "product": "Widget B", "status": "processing"},
    {"id": "ORD-003", "customer": "Gamma Inc", "product": "Widget C", "status": "pending"},
]


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/orders")

    if http_method == "GET" and path == "/orders":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"orders": ORDERS, "count": len(ORDERS)})
        }

    elif http_method == "POST" and path == "/orders":
        body = json.loads(event.get("body", "{}"))
        new_order = {
            "id": f"ORD-{datetime.now().strftime('%H%M%S')}",
            "customer": body.get("customer", "Unknown"),
            "product": body.get("product", "Unknown"),
            "status": "pending"
        }
        ORDERS.append(new_order)
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Order created", "order": new_order})
        }

    return {
        "statusCode": 404,
        "body": json.dumps({"error": "Not found"})
    }
```

### `tests/test_handler.py`

```python
import json
from src.handler import lambda_handler


def test_get_orders():
    event = {"httpMethod": "GET", "path": "/orders"}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "orders" in body
    assert body["count"] == 3


def test_post_order():
    event = {
        "httpMethod": "POST",
        "path": "/orders",
        "body": json.dumps({"customer": "Test Co", "product": "Widget X"})
    }
    response = lambda_handler(event, None)
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["order"]["customer"] == "Test Co"
    assert body["order"]["status"] == "pending"


def test_not_found():
    event = {"httpMethod": "DELETE", "path": "/orders"}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 404
```

### `template.yaml` (SAM)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Demo Orders API - CI/CD Pipeline Session 3

Globals:
  Function:
    Timeout: 30
    Runtime: python3.12
    MemorySize: 128

Resources:
  OrdersFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: demo-orders-api
      Handler: src/handler.lambda_handler
      CodeUri: .
      AutoPublishAlias: live
      DeploymentPreference:
        Type: AllAtOnce
        # Options: Canary10Percent5Minutes, Linear10PercentEvery1Minute, AllAtOnce
        Alarms:
          - !Ref OrdersFunctionErrorsAlarm
      Events:
        GetOrders:
          Type: Api
          Properties:
            Path: /orders
            Method: get
        PostOrder:
          Type: Api
          Properties:
            Path: /orders
            Method: post

  OrdersFunctionErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: demo-orders-api-errors
      MetricName: Errors
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: FunctionName
          Value: demo-orders-api

Outputs:
  ApiUrl:
    Description: API Gateway endpoint URL
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/orders"
  FunctionArn:
    Description: Lambda function ARN
    Value: !GetAtt OrdersFunction.Arn
```

### `buildspec.yml`

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - pip install pytest
      - pip install aws-sam-cli

  pre_build:
    commands:
      - echo "Running unit tests..."
      - python -m pytest tests/ -v
      - echo "Tests passed!"

  build:
    commands:
      - echo "Building SAM application..."
      - sam build
      - sam package --output-template-file packaged.yaml --s3-bucket ${ARTIFACT_BUCKET}

artifacts:
  files:
    - packaged.yaml
  discard-paths: yes
```

---

## Pipeline Configuration

### CodeCommit Repository

| Setting | Value |
|---------|-------|
| Name | `demo-orders-api` |
| Branch | `main` |
| Description | Demo Orders API for CI/CD enablement session |

### CodeBuild Project

| Setting | Value |
|---------|-------|
| Name | `demo-orders-api-build` |
| Source | CodeCommit (`demo-orders-api`, branch `main`) |
| Environment | Managed image, Amazon Linux 2023, Standard 7.0 |
| Compute | `BUILD_GENERAL1_SMALL` (3 GB, 2 vCPU) |
| Buildspec | `buildspec.yml` (in source) |
| Artifacts | S3 bucket (`demo-pipeline-artifacts-dev`) |

**Environment variables:**

| Name | Value |
|------|-------|
| `ARTIFACT_BUCKET` | `demo-pipeline-artifacts-dev` |

### CodePipeline

| Setting | Value |
|---------|-------|
| Name | `demo-orders-api-pipeline` |
| Version | V2 |

**Stages:**

| Stage | Action | Provider | Config |
|-------|--------|----------|--------|
| **Source** | SourceAction | CodeCommit | Repo: `demo-orders-api`, Branch: `main`, trigger on push |
| **Build** | BuildAction | CodeBuild | Project: `demo-orders-api-build` |
| **Deploy** | DeployAction | CloudFormation | Action: CREATE_UPDATE, Stack: `demo-orders-api-stack`, Template: `packaged.yaml`, Capabilities: CAPABILITY_IAM + CAPABILITY_AUTO_EXPAND (SAM triggers CodeDeploy automatically via `DeploymentPreference`) |

---

## IAM Roles

### CodePipeline Service Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["codecommit:GetBranch", "codecommit:GetCommit", "codecommit:UploadArchive", "codecommit:GetUploadArchiveStatus"],
      "Resource": "arn:aws:codecommit:eu-west-1:*:demo-orders-api"
    },
    {
      "Effect": "Allow",
      "Action": ["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudformation:*"],
      "Resource": "arn:aws:cloudformation:eu-west-1:*:stack/demo-orders-api-stack/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::demo-pipeline-artifacts-dev/*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": "*"
    }
  ]
}
```

### CodeBuild Service Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::demo-pipeline-artifacts-dev/*"
    },
    {
      "Effect": "Allow",
      "Action": ["codecommit:GitPull"],
      "Resource": "arn:aws:codecommit:eu-west-1:*:demo-orders-api"
    }
  ]
}
```

### CloudFormation Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:*",
        "apigateway:*",
        "iam:CreateRole", "iam:DeleteRole", "iam:AttachRolePolicy",
        "iam:DetachRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
        "iam:GetRole", "iam:PassRole",
        "cloudformation:CreateChangeSet",
        "s3:GetObject"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Demo Flow (10 min)

| Step | Action | What audience sees |
|------|--------|-------------------|
| 1 | Show CodeCommit repo — `handler.py`, `buildspec.yml`, `template.yaml` | Source code structure |
| 2 | Make a code change: edit response message in `handler.py` | `git add . && git commit -m "Update response" && git push` |
| 3 | Pipeline triggers automatically | CodePipeline console → Source stage ✅ |
| 4 | Build stage runs | CodeBuild → show logs: tests pass, SAM builds |
| 5 | Deploy stage runs | CloudFormation creates changeset → triggers CodeDeploy |
| 6 | **Show CodeDeploy deployment** | CodeDeploy console → deployment in progress, traffic shifting to new version |
| 7 | Show Lambda versions + alias | Lambda console → Versions tab shows v1, v2; `live` alias points to new version |
| 8 | Test the API | `curl https://{api-id}.execute-api.eu-west-1.amazonaws.com/Prod/orders` |
| 9 | Show updated response | New message confirms CodeDeploy shifted traffic successfully |

**Key message:** *"One git push → tests run → package built → CodeDeploy shifts traffic safely → if errors spike, automatic rollback. That's CI/CD on AWS."*

---

## IaC Preference

Use **AWS SAM (YAML)** for the application stack + **AWS CDK (TypeScript)** or **CloudFormation** for the pipeline infrastructure itself.
