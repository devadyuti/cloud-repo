# cloud-repo

Demos, reference implementations and prototypes built on AWS. Each top-level folder is a self-contained project with its own tooling and deployment. Most have a README with full instructions.

All data in this repository is synthetic. AWS account IDs and domains are placeholders (`123456789012`, `example.com`). Replace them with your own values before deploying.

## Projects

| Folder | What it is | Stack |
|---|---|---|
| `agent-core-mcp-demo/` | Two AWS Labs MCP servers (S3 Tables, Redshift) on Bedrock AgentCore Runtime behind an AgentCore Gateway, with a Strands agent for natural-language analytics | Python, CDK, AgentCore |
| `agent-ops-demo/` | Operations layer for an existing agent: traces, an observable policy denial, and deterministic plus LLM-as-judge evaluation | Python, AgentCore |
| `amplify-nuxt-cors/` | Reproduction of Amplify Hosting SSG routing issues (direct-URL 404s, SPA rewrite conflicts) and CORS behaviour | Nuxt 3, Amplify Hosting |
| `bedrock-mantle-access/` | Lambda calling OpenAI models through the Bedrock Mantle endpoint, API key held in Secrets Manager | Python 3.12, SAM |
| `ci-cd-pipeline/` | Orders API deployed by CodePipeline V2 with CodeDeploy traffic shifting and alarm-based rollback | Python 3.12, SAM, CDK |
| `claude-code-bedrock-setup/` | One-command setup of Claude Code on Amazon Bedrock for macOS and Windows | Shell, PowerShell |
| `client-portfolio-risk-dashboard/` | Wealth-management portfolio risk dashboard with Bedrock-generated rebalancing suggestions | React 18, Lambda (Node.js 22), DynamoDB, Bedrock |
| `consumer-regulatory-agent/` | Compliance assessment agent for consumer regulatory requirements | Python 3.12, CDK, AgentCore, DynamoDB |
| `devicefarm-demo/` | Appium tests for a sample Android banking app run on AWS Device Farm | Python, pytest, Appium |
| `document-repo/` | Markdown document viewer reading from S3 | React 18, Amplify, S3, Cognito |
| `kiro-custom-powers/` | Kiro "power" definitions (`POWER.md` + `mcp.json`) that wire up MCP servers | Markdown, JSON |
| `legacy-php-contact-app/` | Small legacy PHP app used to demo Kiro QA review agents and steering files | PHP, MySQL |
| `legal-doc-search/` | Streamlit front end for a legal document search agent | Python, Streamlit |
| `modern-data-architecture/` | Data lake, ingestion, security, analytics and act-on-data streams as CloudFormation templates with Lambda helpers | CloudFormation, Python |
| `mwaa-demo/` | Amazon MWAA demos: classic environment (`classic/`), MWAA Serverless (`serverless/`) and Airflow version upgrade notes | Python, CDK, Airflow, dbt |
| `redshift-serverless-demos/` | Three short Redshift demos: Amazon Q generative SQL, auto-copy from S3, and cross-cluster data sharing | SQL, shell |
| `s3-eventbridge-glue-s3-demo/` | Event-driven ETL: S3 upload → EventBridge → Glue job (CSV to Parquet) → S3 | Python 3.12, CDK |
| `sagemaker-python-sdk-best-practice/` | Reference SageMaker train and inference pipeline using Processing Jobs with a custom container | Python, SageMaker SDK, Docker |
| `waf-ai-monetization-demo/` | AWS WAF Bot Control returning HTTP 402 with an x402 price manifest to AI bots on a CloudFront site | Python 3.12, CDK, CloudFront, WAF |

Supporting folders:

- `.kiro/` holds Kiro specs (requirements, design, tasks), steering files and hooks.
- `generated-diagrams/` holds architecture diagram PNGs.

## Prerequisites

- Node.js 22.x for the JavaScript projects
- Python 3.12+ for the CDK, SAM and agent projects
- AWS CLI v2 with a configured profile
- Serverless Framework 4 (`npm install -g serverless`) for the Serverless projects
- AWS CDK, run per project with `npx cdk`
- Optional: `uv` for the AgentCore projects

Default region is `eu-west-1`. Bedrock projects use cross-region inference profiles. Device Farm runs in `us-west-2`.

## Quick start

### client-portfolio-risk-dashboard

```bash
cd client-portfolio-risk-dashboard/backend
npm install
npx serverless deploy --stage dev   # Lambda + API Gateway + DynamoDB
npm run seed                        # seed DynamoDB with mock clients

cd ../frontend
npm install
npm start                           # http://localhost:3000
```

Set `REACT_APP_API_URL` in `.env` or in the Amplify console.

### consumer-regulatory-agent

```bash
cd consumer-regulatory-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest
cdk deploy --profile <your-profile>
```

Set `account` and `region` in `cdk.json` or pass them with `--context`.

### document-repo

```bash
cd document-repo
npm install
npx serverless deploy --stage dev   # S3 bucket + Cognito identity pool
npm run dev                         # http://localhost:16401
```

Create `.env` with:

```
REACT_APP_BUCKET_NAME=<bucket-name>
REACT_APP_REGION=eu-west-1
REACT_APP_IDENTITY_POOL_ID=<pool-id>
```

### amplify-nuxt-cors

```bash
cd amplify-nuxt-cors
cp .env.example .env                # set your Sanity project URL
npm install
npm run dev                         # http://localhost:3000
npm run generate                    # static build for Amplify
```

Open `/diagnostics` to test route and CORS behaviour.

For every other project, see the README in its folder.

## Conventions

- Plain JavaScript (ESM, no TypeScript), React 18 with Cloudscape, Amplify JS v6.
- One Lambda function per API endpoint. AWS SDK packages go in `devDependencies` because the Lambda runtime provides them.
- DynamoDB uses single-table design with `PK`/`SK` composite keys.
- Python projects use CDK (`aws-cdk-lib`), pytest and moto.
- Account IDs come from env vars or CDK context, never hard-coded.

## Notes and gotchas

### Amplify SSG routing

Amplify's default SPA catch-all rewrite sends every clean URL to `/index.html`, which breaks Nuxt SSG and other pre-rendered sites. Remove that rule so Amplify serves `/route` from `route/index.html`. `amplify-nuxt-cors/README.md` has the full analysis.

### Bedrock cross-region inference profiles

Wildcard the region in IAM resource ARNs. Otherwise calls fail when Bedrock routes the request to another region.

```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": [
    "arn:aws:bedrock:*:ACCOUNT_ID:inference-profile/eu.anthropic.claude-sonnet-4-6",
    "arn:aws:bedrock:*::foundation-model/*"
  ]
}
```

### Deploying

- **Serverless:** check the region in `serverless.yml`. Use `npx serverless deploy --verbose` for CloudFormation events and `npx serverless remove` to tear down.
- **CDK:** run `cdk bootstrap aws://ACCOUNT/REGION` once per account and region, then `cdk synth` and `cdk diff` before `cdk deploy`. Use `cdk destroy` to tear down.
- **Amplify:** keep `amplify.yml` in the repo, set environment variables in the console, and run `npm run build` locally before pushing.
- Several demos create billable resources (MWAA, Redshift, WAF, AgentCore). Tear them down when you finish.

## License

See [LICENSE](LICENSE).
