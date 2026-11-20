# CI/CD Pipeline — Demo Orders API

Fully automated CI/CD pipeline deploying a REST API (API Gateway + Lambda) using CodeCommit → CodeBuild → CodePipeline → CloudFormation → CodeDeploy (traffic shifting via SAM `DeploymentPreference`).

## Architecture

```
CodeCommit (push) → CodePipeline V2 → CodeBuild (test + SAM package) → CloudFormation (deploy) → CodeDeploy (traffic shift) → API Gateway + Lambda (alias: live)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/orders` | Returns list of sample orders |
| POST | `/orders` | Creates a new order (mock) |

## Project Structure

```
ci-cd-pipeline/
├── src/
│   └── handler.py          # Lambda function code
├── tests/
│   └── test_handler.py     # Unit tests
├── infra/                   # CDK infrastructure (pipeline provisioning)
│   ├── app.py              # CDK app entry point
│   ├── pipeline_stack.py   # Pipeline stack definition
│   ├── cdk.json            # CDK config
│   └── requirements.txt    # CDK Python dependencies
├── template.yaml           # SAM template (API GW + Lambda + CodeDeploy)
├── buildspec.yml           # CodeBuild build instructions
└── README.md
```

## How CodeDeploy Fits In

The SAM template declares `AutoPublishAlias: live` and `DeploymentPreference` on the Lambda function. When CloudFormation deploys the stack, SAM automatically:

1. Publishes a new Lambda version
2. Creates/updates a CodeDeploy application and deployment group
3. Shifts traffic from the old version to the new via the `live` alias
4. Monitors the CloudWatch alarm — rolls back if errors spike

No explicit CodeDeploy stage is needed in the pipeline; it's triggered by CloudFormation during the Deploy stage.

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS CDK CLI (`npm install -g aws-cdk`)
- Python 3.12+
- SAM CLI (for local testing)

## Deploy the Pipeline Infrastructure

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap   # first time only
cdk deploy
```

## Push Application Code to Trigger the Pipeline

```bash
# Clone the CodeCommit repo (URL shown in CDK output)
git clone <RepositoryCloneUrl>
cd demo-orders-api

# Copy application files
cp -r ../src ../tests ../template.yaml ../buildspec.yml .

# Push to main
git add .
git commit -m "Initial commit - Orders API"
git push origin main
```

The pipeline triggers automatically on push to `main`.

## Run Tests Locally

```bash
cd ci-cd-pipeline
pip install pytest
python -m pytest tests/ -v
```

## Configuration

| Setting | Value |
|---------|-------|
| Region | `eu-west-1` |
| Runtime | Python 3.12 |
| Lambda memory | 128 MB |
| Lambda timeout | 30s |
| Pipeline type | V2 |
| Deployment strategy | AllAtOnce (configurable) |
| Rollback trigger | CloudWatch Errors alarm |
