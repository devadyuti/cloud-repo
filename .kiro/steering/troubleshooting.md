---
inclusion: manual
---

# Troubleshooting Guide

## Common Issues

### Frontend

**Blank page after build:**
- Check browser console for errors
- Verify `REACT_APP_API_URL` is set correctly
- Ensure `homepage` in package.json matches deployment path (or remove it)

**API calls returning CORS errors:**
- Verify `httpApi.cors: true` in serverless.yml
- Check the API URL doesn't have a trailing slash
- Ensure Amplify env var matches the actual API Gateway URL

**Cloudscape components not rendering:**
- Import `@cloudscape-design/global-styles/index.css` in index.jsx
- Check component import paths (tree-shakeable: `@cloudscape-design/components/button`)

**Recharts not displaying:**
- Ensure parent container has explicit width/height
- Use `ResponsiveContainer` wrapper with width="100%" height={300}

### Backend

**Lambda returning 502:**
- Check CloudWatch logs: `npx serverless logs -f functionName`
- Verify handler export name matches serverless.yml
- Ensure response has `statusCode` and `body` (stringified)

**DynamoDB access denied:**
- Verify table name in env var matches actual table
- Check IAM role has correct actions for the table ARN
- Ensure region in ARN matches deployment region

**Bedrock InvokeModel access denied:**
- Use wildcard region in IAM: `arn:aws:bedrock:*:ACCOUNT:...`
- Verify model access is enabled in Bedrock console
- Check inference profile ID is correct

**Serverless deploy fails:**
- Run `npx serverless package` first to validate
- Check CloudFormation events: `npx serverless deploy --verbose`
- Verify AWS credentials are fresh (ada/isengard)

### Amplify Hosting

**404 on direct URL access (SSG apps):**
- Remove the SPA catch-all rewrite rule from Amplify console
- Amplify's default static serving handles `/route` → `route/index.html`

**Build fails in Amplify:**
- Check build logs in Amplify console
- Verify Node.js version matches (set in amplify.yml build settings)
- Ensure all env vars are configured in Amplify console

### Credentials

**Expired AWS credentials:**
```bash
# Refresh with ada
ada credentials update --account ACCOUNT_ID --profile claude-bedrock --role ROLE --once

# Verify
aws sts get-caller-identity --profile claude-bedrock
```

## Useful Debug Commands

```bash
# Check deployed API endpoints
npx serverless info --stage dev

# Tail Lambda logs in real-time
npx serverless logs -f functionName --tail

# Test API locally (requires serverless-offline plugin)
npx serverless offline

# Validate serverless config
npx serverless print

# Check DynamoDB table contents
aws dynamodb scan --table-name ClientPortfolios-dev --region eu-west-1
```
