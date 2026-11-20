---
inclusion: auto
description: "Use when deploying to AWS Amplify, configuring Amplify hosting, setting up CI/CD, or troubleshooting Amplify build issues"
---

# Skill: AWS Amplify Deployment

## Setup

### amplify.yml (Build Specification)

Place in the frontend project root:

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

### Environment Variables

Set in Amplify Console → App settings → Environment variables:

| Variable | Example | Purpose |
|----------|---------|---------|
| `REACT_APP_API_URL` | `https://abc123.execute-api.eu-west-1.amazonaws.com` | API Gateway endpoint |
| `REACT_APP_REGION` | `eu-west-1` | AWS region for SDK |

**Important:** `REACT_APP_*` prefix is required for Create React App to embed vars at build time.

## Deployment Workflow

### Initial Setup (Amplify Console)

1. Connect Git repository (branch: `main`)
2. Amplify auto-detects build settings from `amplify.yml`
3. Set environment variables
4. Deploy

### Subsequent Deploys

Push to `main` → Amplify auto-builds and deploys.

For manual redeploy: Amplify Console → App → Redeploy this version.

## Common Issues & Fixes

### 404 on page refresh (SPA routing)

**Problem:** Direct URL access returns 404 for client-side routes.

**Fix for React SPA:** Add a custom rewrite rule in Amplify Console → Rewrites and redirects:

| Source | Target | Type |
|--------|--------|------|
| `</^[^.]+$\|\.(?!(css\|gif\|ico\|jpg\|js\|png\|txt\|svg\|woff\|woff2\|ttf\|map\|json\|webp)$)([^.]+$)/>` | `/index.html` | 200 (Rewrite) |

**Fix for SSG (Nuxt, Next static):** REMOVE the above rule. Amplify's default static serving handles pre-rendered routes correctly.

### Build fails — missing env vars

**Symptom:** App builds but API calls fail (undefined URL).

**Fix:** Verify env vars are set in Amplify Console. They must be set BEFORE the build runs. Trigger a new build after adding them.

### Build fails — Node version mismatch

Add to `amplify.yml`:
```yaml
frontend:
  phases:
    preBuild:
      commands:
        - nvm use 22
        - npm ci
```

### CORS errors after deploy

**Checklist:**
1. API Gateway has `httpApi.cors: true` in serverless.yml
2. `REACT_APP_API_URL` matches the actual deployed API URL (no trailing slash)
3. API is deployed to the same stage referenced in the URL

## Amplify + Serverless Framework Integration

The typical flow for this project:

1. Deploy backend first: `cd backend && npx serverless deploy --stage dev`
2. Copy the API endpoint from deploy output
3. Set `REACT_APP_API_URL` in Amplify Console
4. Push frontend code → Amplify builds and deploys

## Checklist

- [ ] `amplify.yml` present in frontend root
- [ ] Environment variables set in Amplify Console
- [ ] `REACT_APP_*` prefix used for all frontend env vars
- [ ] Backend deployed before frontend (API URL must exist)
- [ ] Correct rewrite rule for SPA vs SSG
- [ ] Node.js version specified if not using Amplify default
