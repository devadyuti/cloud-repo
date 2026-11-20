# Client Portfolio Risk Dashboard

A Wealth Management Client Portfolio Risk Dashboard for investment managers to monitor client portfolios, assess risk exposure, and receive AI-powered rebalancing suggestions.

## What It Does

- **Client Overview** — View all clients with portfolio value, risk profile, and last review date
- **Portfolio Detail** — Drill into any client to see asset allocation (pie chart), top 10 holdings, and risk metrics
- **AI Insights** — Generate actionable rebalancing suggestions from Amazon Bedrock (Claude) based on current allocation vs target
- **Risk Alerts** — Automatic warnings when portfolios breach equity overweight or volatility thresholds

## Architecture

```
Browser → AWS Amplify (static hosting)
           ↓ REST calls (Amplify API)
       API Gateway (httpApi, CORS enabled)
           ↓
       AWS Lambda (Node.js 22, one function per endpoint)
           ↓                    ↓
       DynamoDB              Amazon Bedrock
       (single-table)       (Claude cross-region inference)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Cloudscape Design System, Amplify JS SDK v6 |
| Backend | AWS Lambda (Node.js 22), Serverless Framework 4 |
| API | API Gateway HTTP API (httpApi) with automatic CORS |
| Database | DynamoDB (single-table, PK/SK design, on-demand billing) |
| AI | Amazon Bedrock — `eu.anthropic.claude-sonnet-4-6` inference profile |
| Hosting | AWS Amplify (frontend), Lambda (backend) |
| Region | eu-west-1 |

### Key Design Decisions

- **No TypeScript** — Plain JavaScript throughout (frontend and backend)
- **One Lambda per endpoint** — Each API route is its own function in `serverless.yml`, not a monolithic router
- **Amplify REST API** — Frontend uses `aws-amplify/api` (`get`/`post`) instead of raw `fetch`
- **Cloudscape PieChart** — No external charting library; uses Cloudscape's built-in `PieChart` component
- **AWS SDK not bundled** — SDK packages are in `devDependencies` since Lambda runtime provides them natively
- **Cross-region inference profile** — Uses `eu.anthropic.claude-sonnet-4-6` which routes across EU regions; IAM wildcards the region accordingly
- **Client-side risk alerts** — Computed from portfolio data already fetched; no extra API call

## Project Structure

```
client-portfolio-risk-dashboard/
├── frontend/
│   ├── src/
│   │   ├── components/       # 10 React components (Cloudscape)
│   │   ├── api/client.js     # Amplify REST API client
│   │   ├── utils/            # formatters.js, riskCalculations.js
│   │   ├── App.jsx           # Main app with state management
│   │   └── index.jsx         # Entry point, Amplify.configure()
│   ├── public/index.html
│   ├── amplify.yml           # Amplify build settings
│   └── package.json
├── backend/
│   ├── src/
│   │   ├── routes/           # clients.js, portfolio.js, insights.js
│   │   └── services/         # dynamodb.js, bedrock.js
│   ├── scripts/seed.js       # DynamoDB seed script
│   ├── serverless.yml        # Infrastructure + functions
│   └── package.json
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/clients` | List all clients |
| GET | `/clients/{id}` | Get single client |
| GET | `/clients/{id}/portfolio` | Get portfolio (allocation, holdings, risk metrics) |
| POST | `/clients/{id}/insights` | Generate AI rebalancing suggestions |

## DynamoDB Schema

Single table `ClientPortfolios-{stage}` with composite key:

| PK | SK | Contains |
|----|-----|----------|
| `CLIENT#CLT001` | `PROFILE` | Client name, value, risk profile, review date |
| `CLIENT#CLT001` | `PORTFOLIO` | Allocation, holdings array, risk metrics |

## Getting Started

### Prerequisites

- Node.js 22+
- AWS CLI configured (eu-west-1)
- Serverless Framework 4 (`npm install -g serverless`)

### Deploy Backend

```bash
cd backend
npm install
npx serverless deploy --stage dev
npm run seed
```

This creates the DynamoDB table, deploys 4 Lambda functions, and seeds 5 mock clients with portfolios.

### Run Frontend Locally

```bash
cd frontend
npm install
```

Create `.env`:
```
REACT_APP_API_URL=https://<your-api-id>.execute-api.eu-west-1.amazonaws.com
```

```bash
npm start
```

### Deploy Frontend (Amplify)

Connect the repo to AWS Amplify. The `amplify.yml` handles the build. Set `REACT_APP_API_URL` as an environment variable in the Amplify console.

## Mock Data

5 clients with distinct profiles:

| ID | Name | Value | Risk Profile |
|----|------|-------|-------------|
| CLT001 | Smith Family Trust | £2.45M | Balanced |
| CLT002 | Dr. Sarah Mitchell | £890K | Growth |
| CLT003 | Henderson Charitable Foundation | £5.2M | Conservative |
| CLT004 | Mr. & Mrs. Patel | £1.75M | Balanced |
| CLT005 | Westbury Pension Scheme | £8.9M | Conservative |

Each client has 10 holdings, allocation across 5 asset classes, and risk metrics (volatility, Sharpe ratio, max drawdown, beta vs FTSE 100).

## Branding

- Primary: Navy Blue (#1B365D) — header/navigation
- Accent: Gold (#B8860B) — buttons, insight card borders
- Background: Light Grey (#F5F5F5)
- Font: Inter
