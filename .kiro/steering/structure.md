# Project Structure

## Repository Layout

```
aws-architecture-analysis/
├── .kiro/
│   ├── specs/          # Kiro specifications (requirements, design, tasks)
│   ├── steering/       # This directory — project guidance
│   └── hooks/          # Agent automation hooks
├── client-portfolio-risk-dashboard/
│   ├── frontend/       # React 18 SPA (Amplify-hosted)
│   │   ├── src/
│   │   │   ├── components/   # Flat component directory
│   │   │   ├── api/          # API client functions
│   │   │   ├── utils/        # Shared utilities
│   │   │   └── types/        # JSDoc type definitions
│   │   ├── public/
│   │   ├── amplify.yml
│   │   └── package.json
│   └── backend/        # Serverless Framework 4 API
│       ├── src/
│       │   ├── routes/       # Lambda handler functions
│       │   ├── services/     # Business logic (Bedrock, etc.)
│       │   └── data/         # Mock data / DynamoDB access
│       ├── scripts/          # Utility scripts (seed, etc.)
│       ├── serverless.yml
│       └── package.json
├── consumer-regulatory-agent/   # Python CDK + AgentCore
├── document-repo/               # React + S3 document viewer
├── amplify-nuxt-cors/           # Nuxt 3 SSG reproduction
├── claude-code-bedrock-setup/   # Shell setup scripts
├── docs/                        # Customer engagement docs
└── README.md                    # Repository overview
```

## Adding New Features

### Frontend (React)
1. Create component in `frontend/src/components/ComponentName.jsx`
2. Import and use in `App.jsx` or parent component
3. API calls go in `frontend/src/api/` as named exports
4. Utility functions in `frontend/src/utils/`

### Backend (Lambda)
1. Add handler function in `backend/src/routes/` (one file per resource)
2. Business logic in `backend/src/services/`
3. Register the function and HTTP event in `serverless.yml`
4. Keep handlers under 30s timeout (default 10s, Bedrock calls 30s)

### New Project
1. Create directory at repository root
2. Choose pattern: Serverless Framework, CDK, or Amplify
3. Add project-specific README
4. Add the project to the table in README.md
