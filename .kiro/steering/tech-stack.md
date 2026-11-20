# Tech Stack & Conventions

## JavaScript / Node.js

- **Runtime:** Node.js 22.x
- **No TypeScript** — Plain JavaScript throughout all projects
- **Module system:** ESM (`"type": "module"` in package.json)
- **Frontend:** React 18 with JSX (`.jsx` files, not `.tsx`)
- **Component library:** Cloudscape Design System (AWS internal design system)
- **Charting:** Recharts for data visualisation
- **API client:** AWS Amplify JS SDK v6 (`aws-amplify/api` — `get`, `post`)
- **Backend:** AWS Lambda handlers with ESM exports
- **Package manager:** npm (not yarn or pnpm)

## Python

- **Runtime:** Python 3.12+
- **Infrastructure:** AWS CDK (`aws-cdk-lib`)
- **Agent framework:** Strands Agents (Bedrock AgentCore)
- **Testing:** pytest with moto for AWS service mocking
- **Package management:** pip + pyproject.toml

## Coding Standards

- No TypeScript — do not introduce `.ts` or `.tsx` files
- Use `const` and arrow functions for Lambda handlers
- One Lambda function per API endpoint (not monolithic routers)
- AWS SDK packages go in `devDependencies` (Lambda runtime provides them)
- Use named exports for handler functions
- Keep Lambda handlers thin — business logic in `src/services/`
- Data access in `src/data/` or `src/routes/`
- Frontend components are flat in `src/components/` (no nested folders)
- No prop-types or runtime type checking — use JSDoc comments if needed

## Naming Conventions

- **Files:** camelCase for JS (`clientList.js`), PascalCase for React components (`ClientListView.jsx`)
- **Functions:** camelCase (`listClients`, `getPortfolio`)
- **Lambda handlers:** Named exports matching the function name in `serverless.yml`
- **DynamoDB keys:** PK/SK composite key pattern (single-table design)
- **Environment variables:** UPPER_SNAKE_CASE (`TABLE_NAME`, `REACT_APP_API_URL`)

## Dependencies — Do Not Introduce

- TypeScript or type-checking libraries
- Express, Fastify, or other HTTP frameworks in Lambda
- Moment.js (use native Date or lightweight alternatives)
- jQuery or legacy DOM libraries
- CSS-in-JS libraries (styled-components, emotion) — use plain CSS or Cloudscape tokens
