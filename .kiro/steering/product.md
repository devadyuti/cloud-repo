# Product Context

## Repository Overview

This is a multi-project AWS architecture workspace containing customer engagement projects, technical demonstrations, and internal tools built on AWS services. Projects are independent with their own deployment workflows.

## Active Projects

| Project | Purpose | Stack |
|---------|---------|-------|
| `client-portfolio-risk-dashboard/` | Wealth management portfolio risk dashboard demo | React 18, Lambda Node.js 22, DynamoDB, Bedrock |
| `consumer-regulatory-agent/` | Compliance assessment agent | Python 3.12, CDK, Bedrock AgentCore |
| `document-repo/` | Markdown document viewer SPA | React 18, Amplify, S3, Cognito |
| `amplify-nuxt-cors/` | Amplify SSG routing reproduction | Nuxt 3, Amplify Hosting |
| `claude-code-bedrock-setup/` | Team onboarding automation | Shell scripts |

## Key Design Principles

- Each project is self-contained at the repository root
- Serverless-first architecture (Lambda, API Gateway, DynamoDB)
- AWS Amplify for static frontend hosting
- Amazon Bedrock for AI capabilities (cross-region inference profiles)
- Demo-quality code — functional prototypes, not production systems
- No authentication unless explicitly required by the project spec

## AWS Defaults

- **Region:** `eu-west-1` (primary), `us-east-1` (Bedrock inference profiles)
- **Deployment:** Serverless Framework 4 (APIs), AWS CDK (infra), Amplify (frontends)
- **Account:** References use env vars or context — never hardcoded
