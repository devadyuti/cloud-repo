---
inclusion: manual
---

# AWS Deployment Guide

## Serverless Framework Deployment

```bash
cd client-portfolio-risk-dashboard/backend
npx serverless deploy --stage dev          # Deploy to dev
npx serverless deploy --stage prod         # Deploy to production (confirm first!)
npx serverless logs -f functionName        # View Lambda logs
npx serverless remove --stage dev          # Tear down stack
```

### Pre-deployment Checklist
1. Verify AWS CLI profile: `aws configure list`
2. Confirm region matches `serverless.yml`
3. For Bedrock: ensure model access is enabled in the console
4. Run `npx serverless package` to validate before deploying

## AWS Amplify Frontend Deployment

- Amplify auto-deploys from the `main` branch
- Build settings defined in `amplify.yml`
- Environment variables set in Amplify console (not committed)
- Required env var: `REACT_APP_API_URL` pointing to API Gateway endpoint

### Amplify Build Settings (amplify.yml)
```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: build
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

## CDK Deployment (Python projects)

```bash
cd consumer-regulatory-agent
source .venv/bin/activate
cdk synth                    # Validate template
cdk diff                     # Preview changes
cdk deploy                   # Deploy (prompts for approval)
cdk destroy                  # Tear down (DESTRUCTIVE — confirm!)
```

## DynamoDB Seeding

```bash
cd client-portfolio-risk-dashboard/backend
npm run seed                 # Populates table with mock client data
```

## Troubleshooting

- **CORS errors:** Verify `httpApi.cors: true` in serverless.yml and that the frontend URL is correct
- **Bedrock permission denied:** Check IAM policy uses wildcard region for inference profiles
- **Amplify 404s on refresh:** Remove SPA catch-all rewrite rule (see amplify-nuxt-cors README)
- **Lambda timeout:** Increase timeout in serverless.yml (max 30s for Bedrock calls)
- **DynamoDB access denied:** Verify table name matches `TABLE_NAME` env var and IAM resource ARN
