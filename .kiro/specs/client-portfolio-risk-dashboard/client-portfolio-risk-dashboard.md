
# Functional Spec: Client Portfolio Risk Dashboard
## A Kiro Demo Use Case for AnyCompany Wealth

---

## Overview

A lightweight **Client Portfolio Risk Dashboard** that allows Wealth Management investment managers to quickly view client portfolio allocations, assess risk exposure, and receive AI-generated rebalancing suggestions. This demonstrates Kiro's spec-driven development approach to rapidly build a functional wealth management tool.

---

## Tech Stack

| Layer      | Technology                                          |
| ------------| -----------------------------------------------------|
| Frontend   | React 18 (SPA)                                      |
| Backend    | AWS Lambda (Node.js 22) via Serverless Framework 4  |
| API        | API Gateway with REST endpoints                     |
| Deployment | AWS Amplify (UI), Serverless Framework (API)        |
| AI         | Amazon Bedrock (Claude) for rebalancing suggestions |
| Data       | Mock JSON data (no database needed for demo)        |

---

## Features (MVP Scope)

### 1. Client Portfolio Overview Page
- Display a list of mock clients (5 sample clients)
- Each client shows: Name, Total Portfolio Value, Risk Profile (Conservative/Balanced/Growth), Last Review Date
- Clickable rows to drill into individual client

### 2. Individual Client Portfolio View
- **Asset Allocation Pie Chart** — showing breakdown by asset class:
    - UK Equities, International Equities, Fixed Income, Alternatives, Cash
- **Holdings Table** — top 10 holdings with: Name, Sector, Value, Weight (%), 1M Change (%)
- **Risk Metrics Panel**:
    - Portfolio Volatility (annualised)
    - Sharpe Ratio
    - Max Drawdown (12M)
    - Beta vs FTSE 100

### 3. AI Rebalancing Suggestions (Bedrock Integration)
- A "Get AI Insights" button that calls Bedrock (Claude)
- Sends current allocation + risk profile to the model
- Returns 3-4 actionable suggestions, e.g.:
    - "Portfolio is overweight UK equities (45%) vs target (35%). Consider reducing by 10% and reallocating to International Fixed Income for diversification."
    - "Cash allocation (12%) exceeds target (5%). With current gilt yields at 4.2%, consider short-duration gilts."
- Display suggestions in a styled card layout

### 4. Risk Alerts Banner
- Top-of-page alerts for portfolios breaching risk thresholds
- E.g., "⚠️ 2 clients exceed maximum equity allocation" or "⚠️ Portfolio volatility above target for Client: Smith Family Trust"

---

## Mock Data Structure

### clients.json
```json
[
  {
    "id": "CLT001",
    "name": "Smith Family Trust",
    "portfolioValue": 2450000,
    "riskProfile": "Balanced",
    "lastReviewDate": "2026-03-15",
    "investmentManager": "James Richardson"
  },
  {
    "id": "CLT002",
    "name": "Dr. Sarah Mitchell",
    "portfolioValue": 890000,
    "riskProfile": "Growth",
    "lastReviewDate": "2026-04-02",
    "investmentManager": "Emma Clarke"
  },
  {
    "id": "CLT003",
    "name": "Henderson Charitable Foundation",
    "portfolioValue": 5200000,
    "riskProfile": "Conservative",
    "lastReviewDate": "2026-02-28",
    "investmentManager": "James Richardson"
  },
  {
    "id": "CLT004",
    "name": "Mr. & Mrs. Patel",
    "portfolioValue": 1750000,
    "riskProfile": "Balanced",
    "lastReviewDate": "2026-04-18",
    "investmentManager": "Sophie Williams"
  },
  {
    "id": "CLT005",
    "name": "Westbury Pension Scheme",
    "portfolioValue": 8900000,
    "riskProfile": "Conservative",
    "lastReviewDate": "2026-01-20",
    "investmentManager": "Emma Clarke"
  }
]
```

### portfolios.json (per client - example for CLT001)
```json
{
  "clientId": "CLT001",
  "allocation": {
    "ukEquities": 38,
    "internationalEquities": 25,
    "fixedIncome": 20,
    "alternatives": 10,
    "cash": 7
  },
  "holdings": [
    { "name": "Shell PLC", "sector": "Energy", "value": 245000, "weight": 10.0, "change1M": 2.3 },
    { "name": "AstraZeneca", "sector": "Healthcare", "value": 220000, "weight": 9.0, "change1M": -1.2 },
    { "name": "Unilever", "sector": "Consumer Staples", "value": 195000, "weight": 8.0, "change1M": 0.8 },
    { "name": "HSBC Holdings", "sector": "Financials", "value": 180000, "weight": 7.3, "change1M": 3.1 },
    { "name": "iShares Core MSCI World", "sector": "Global Equity ETF", "value": 310000, "weight": 12.7, "change1M": 1.5 },
    { "name": "Vanguard US Equity Index", "sector": "US Equity Fund", "value": 245000, "weight": 10.0, "change1M": 2.8 },
    { "name": "UK Gilt 4.25% 2032", "sector": "Fixed Income", "value": 200000, "weight": 8.2, "change1M": 0.3 },
    { "name": "iShares Corp Bond ETF", "sector": "Fixed Income", "value": 150000, "weight": 6.1, "change1M": -0.2 },
    { "name": "Blackstone Infrastructure", "sector": "Alternatives", "value": 130000, "weight": 5.3, "change1M": 1.1 },
    { "name": "Cash & Money Market", "sector": "Cash", "value": 171500, "weight": 7.0, "change1M": 0.4 }
  ],
  "riskMetrics": {
    "volatility": 11.2,
    "sharpeRatio": 0.85,
    "maxDrawdown": -8.4,
    "betaFTSE100": 0.92
  }
}
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /clients | List all clients |
| GET | /clients/{id} | Get client details |
| GET | /clients/{id}/portfolio | Get portfolio allocation & holdings |
| POST | /clients/{id}/insights | Generate AI rebalancing suggestions (calls Bedrock) |

---

## UI Layout (Single Page App)

```
┌─────────────────────────────────────────────────────┐
│  🏦 Wealth Management Portfolio Risk Dashboard              │
│  ⚠️ Risk Alerts Banner                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Client List View]          [Portfolio Detail]     │
│  ┌──────────────────┐       ┌────────────────────┐ │
│  │ Smith Family Trust│  →    │ 🥧 Allocation Chart│ │
│  │ Dr. Sarah Mitchell│       │                    │ │
│  │ Henderson Charity │       │ 📊 Holdings Table  │ │
│  │ Mr & Mrs Patel   │       │                    │ │
│  │ Westbury Pension │       │ 📈 Risk Metrics    │ │
│  └──────────────────┘       │                    │ │
│                              │ 🤖 [Get AI Insights]│ │
│                              │ ┌────────────────┐ │ │
│                              │ │ Suggestion 1   │ │ │
│                              │ │ Suggestion 2   │ │ │
│                              │ │ Suggestion 3   │ │ │
│                              │ └────────────────┘ │ │
│                              └────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## Kiro Spec-Driven Development Flow

### Step 1: Create the Spec (this document)
Feed this functional spec into Kiro to generate:
- User stories with acceptance criteria
- Design document with technical architecture
- Implementation tasks

### Step 2: Kiro Generates Implementation Plan
Kiro will break this into tasks:
1. Scaffold React app with routing
2. Create mock data files
3. Build client list component
4. Build portfolio detail component with charts (use recharts or chart.js)
5. Create Lambda functions for API endpoints
6. Integrate Bedrock for AI insights
7. Add risk alerts logic
8. Style with Wealth Management-inspired branding (navy blue #1B365D, gold #B8860B)

### Step 3: Iterative Build (2-3 hours)
- Use Kiro's task-driven approach to implement each feature
- Demo the progression from spec → working app

---

## Branding Guidelines (for UI)

| Element          | Value　　　　　　　　　　　　　　 |
| ------------------| -----------------------------------|
| Primary Colour   | Navy Blue (#1B365D)　　　　　　　 |
| Secondary Colour | Gold (#B8860B)　　　　　　　　　　|
| Accent           | Light Grey (#F5F5F5)　　　　　　　|
| Font             | Inter or similar clean sans-serif |
| Logo placeholder | "🏦 Wealth Management" text　　　 |

---

## Demo Talking Points

1. **"We started with just a functional spec"** — show this your source document. **"Kiro generated the architecture and tasks"** — show the generated design doc
3. **"In under 3 hours, we have a working prototype"** — demo the app
4. **"The AI insights feature took minutes, not days"** — show Bedrock integration
5. **"This approach scales"** — discuss how Wealth Management could use this for internal tools, client portals, compliance dashboards

---

## Out of Scope (for demo)

- Authentication/authorization
- Real market data feeds
- Database persistence
- Production error handling
- Mobile responsiveness
- Compliance/regulatory features

---

## Success Criteria

- ✅ Client list renders with mock data
- ✅ Clicking a client shows portfolio breakdown with pie chart
- ✅ Holdings table displays correctly
- ✅ Risk metrics panel shows key figures
- ✅ "Get AI Insights" button returns meaningful suggestions from Bedrock
- ✅ Risk alerts banner shows relevant warnings
- ✅ Total build time: under 3 hours with Kiro
