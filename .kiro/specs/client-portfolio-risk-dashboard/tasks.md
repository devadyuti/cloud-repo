# Implementation Plan: Client Portfolio Risk Dashboard

## Overview

Build a Wealth Management Client Portfolio Risk Dashboard as a React 18 SPA frontend with AWS Lambda (Node.js 22) backend functions. All code is plain JavaScript (no TypeScript). The backend uses Serverless Framework 4 with individual Lambda functions per endpoint (httpApi events), a single DynamoDB table (`ClientPortfolios`) with PK/SK single-table design, and Amazon Bedrock for AI insights. The frontend uses Cloudscape Design System components. The implementation follows an incremental approach: scaffold both projects, create mock data seeded into DynamoDB, build backend API endpoints, implement frontend components from simple to complex, integrate Bedrock for AI insights, add risk alerts logic, apply branding, and configure deployment. Optional tasks throughout cover production-readiness concerns (auth, observability, resilience, CI/CD).

## Tasks

- [x] 1. Scaffold project structure
  - [x] 1.1 Create the monorepo folder structure with frontend/ and backend/ directories
    - Create `client-portfolio-risk-dashboard/` root with `frontend/` and `backend/` subdirectories
    - Create `frontend/src/components/`, `frontend/src/utils/`, `frontend/src/api/` directories
    - Create `backend/src/`, `backend/src/routes/`, `backend/src/services/`, `backend/src/data/` directories
    - Add a root `README.md` describing the project
    - _Requirements: 9.1, 9.2_

  - [x] 1.2 Initialise the frontend React 18 project with JavaScript
    - Create `frontend/package.json` with React 18, Recharts, and development dependencies
    - Create `frontend/jsconfig.json` with path aliases and module resolution
    - Create `frontend/public/index.html` with the app mount point and Inter font import
    - Create `frontend/src/index.js` entry point rendering App component
    - _Requirements: 8.4, 9.1_

  - [x] 1.3 Initialise the backend Serverless Framework 4 project with JavaScript
    - Create `backend/package.json` with `@aws-sdk/client-bedrock-runtime`, `@aws-sdk/client-dynamodb`, `@aws-sdk/lib-dynamodb`, and dev dependencies
    - Create `backend/serverless.yml` with service name, provider (Node.js 22, eu-west-1), separate Lambda functions for each API endpoint (listClients, getClient, getPortfolio, generateInsights), CORS configuration, DynamoDB table resource, and IAM permissions
    - Each function defined with its own handler file and HTTP event — no monolithic handler, no CloudFormation resources block for API Gateway
    - _Requirements: 9.2, 9.3, 9.4_

  - [ ]* 1.4 Add ESLint and Prettier configuration
    - Create `.eslintrc.json` with JavaScript rules for both frontend and backend
    - Create `.prettierrc` with consistent formatting rules
    - Add lint and format scripts to both package.json files
    - _Production: Code quality and consistency_

- [x] 2. Create data layer with DynamoDB
  - [x] 2.1 Define DynamoDB table schema in serverless.yml
    - Add a `ClientPortfolios` DynamoDB table resource with partition key `PK` (String) and sort key `SK` (String)
    - Use single-table design: clients stored as `PK=CLIENT#<id>, SK=PROFILE`, portfolios as `PK=CLIENT#<id>, SK=PORTFOLIO`
    - Add IAM role statements granting the Lambda function DynamoDB read/write access
    - Set billing mode to PAY_PER_REQUEST for the demo
    - _Requirements: 10.1, 10.2_

  - [x] 2.2 Create a seed script to populate DynamoDB with mock data
    - Create `backend/src/scripts/seed.js`
    - Insert all 5 clients: Smith Family Trust (CLT001, Balanced, £2.45M), Dr. Sarah Mitchell (CLT002, Growth, £890K), Henderson Charitable Foundation (CLT003, Conservative, £5.2M), Mr. & Mrs. Patel (CLT004, Balanced, £1.75M), Westbury Pension Scheme (CLT005, Conservative, £8.9M)
    - Insert portfolio data for all 5 clients with allocation, 10 holdings each, and risk metrics
    - Ensure allocations are realistic for each risk profile (Conservative: more fixed income/cash, Growth: more equities, Balanced: mixed)
    - Add an npm script `seed` to run the script against the deployed table
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 2.3 Create a DynamoDB data access layer
    - Create `backend/src/services/dynamodb.js`
    - Instantiate `DynamoDBDocumentClient` with region `eu-west-1` (credentials from Lambda instance profile)
    - Implement `getAllClients()`: Query all items with SK=PROFILE
    - Implement `getClient(id)`: GetItem with PK=CLIENT#<id>, SK=PROFILE
    - Implement `getPortfolio(id)`: GetItem with PK=CLIENT#<id>, SK=PORTFOLIO
    - _Requirements: 2.1, 2.2, 10.3_

  - [ ]* 2.4 Add DynamoDB backup and point-in-time recovery
    - Enable point-in-time recovery on the ClientPortfolios table in serverless.yml
    - Add a note in README about backup/restore procedures
    - _Production: Data durability and disaster recovery_

- [x] 3. Implement backend Lambda handler and API routes
  - [x] 3.1 Implement separate Lambda handlers for each API endpoint
    - Create `backend/src/handlers/listClients.js` — handles GET /clients
    - Create `backend/src/handlers/getClient.js` — handles GET /clients/{id}
    - Create `backend/src/handlers/getPortfolio.js` — handles GET /clients/{id}/portfolio
    - Create `backend/src/handlers/generateInsights.js` — handles POST /clients/{id}/insights
    - Each handler is a standalone exported function with its own HTTP event in serverless.yml
    - Add CORS headers (Access-Control-Allow-Origin: *, Access-Control-Allow-Headers, Access-Control-Allow-Methods) to all responses
    - _Requirements: 2.1, 2.2, 9.3, 9.4_

  - [ ]* 3.2 Add request validation middleware
    - Create `backend/src/middleware/validation.js`
    - Validate path parameters (client ID format: CLT followed by 3 digits)
    - Validate POST /insights request body schema (allocation percentages sum to 100, riskProfile is valid enum)
    - Return 400 with descriptive error messages for invalid requests
    - _Production: Input validation and security_

  - [x] 3.3 Implement listClients and getClient handlers
    - Create `backend/src/handlers/listClients.js` — calls DynamoDB data access layer to return all clients
    - Create `backend/src/handlers/getClient.js` — finds client by ID, returns 404 with `{ error: "Client not found", clientId }` if not found
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.4 Implement getPortfolio handler
    - Create `backend/src/handlers/getPortfolio.js`
    - Calls DynamoDB data access layer to find portfolio by clientId, returns 404 if not found
    - Returns full portfolio object with allocation, holdings, and riskMetrics
    - _Requirements: 3.4, 4.1, 5.1_

  - [x] 3.5 Implement Bedrock service for AI insights
    - Create `backend/src/services/bedrock.js`
    - Instantiate `BedrockRuntimeClient` with region `eu-west-1` (credentials from Lambda instance profile — no explicit keys)
    - Create `generateInsights(allocation, riskProfile, riskMetrics)` function
    - Build prompt template that includes current allocation percentages, risk profile, risk metrics, target allocation ranges per risk profile, and instruction to return exactly 3-4 actionable suggestions with specific percentages
    - Call `InvokeModelCommand` with modelId `eu.anthropic.claude-sonnet-4-6`, anthropic_version `bedrock-2023-05-31`, max_tokens 4096
    - Parse response and extract suggestions array
    - Handle errors gracefully, returning a user-friendly error message
    - _Requirements: 6.2, 6.6_

  - [x] 3.6 Implement generateInsights handler
    - Create `backend/src/handlers/generateInsights.js`
    - Parse request body for allocation, riskProfile, and riskMetrics
    - Call Bedrock service to generate suggestions
    - Return `{ suggestions: string[] }` on success
    - Return 500 with `{ error: "Failed to generate insights. Please try again." }` on failure
    - _Requirements: 6.1, 6.2, 6.5, 6.6_

  - [ ]* 3.7 Add structured logging with correlation IDs
    - Create `backend/src/utils/logger.js` using a structured JSON logger
    - Generate a correlation ID per request (from API Gateway request ID)
    - Log request/response metadata (method, path, status, duration) on every request
    - Log Bedrock call duration and token usage
    - _Production: Observability and debugging_

  - [ ]* 3.8 Add error handling middleware with proper HTTP status codes
    - Create `backend/src/middleware/errorHandler.js`
    - Catch unhandled exceptions and return 500 with generic message (no stack traces in response)
    - Map known error types to appropriate HTTP status codes (400, 404, 429, 500, 503)
    - Log full error details server-side for debugging
    - _Production: Error handling and security (no information leakage)_

  - [ ]* 3.9 Write unit tests for backend handlers
    - Test listClients returns all 5 clients
    - Test getClient returns correct client by ID
    - Test getClient returns 404 for invalid ID
    - Test getPortfolio returns correct portfolio data
    - Test generateInsights returns suggestions array
    - Test request validation rejects malformed input
    - _Production: Test coverage and regression prevention_

- [x] 4. Checkpoint - Ensure backend runs and tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement frontend API client and utility functions
  - [x] 5.1 Create the API client module
    - Create `frontend/src/api/client.js`
    - Implement `fetchClients()`: GET /clients → array of client objects
    - Implement `fetchClient(id)`: GET /clients/{id} → client object
    - Implement `fetchPortfolio(id)`: GET /clients/{id}/portfolio → portfolio object
    - Implement `generateInsights(id, request)`: POST /clients/{id}/insights → insights response
    - Use a configurable base URL (environment variable `REACT_APP_API_URL`) for the API endpoint
    - Include proper error handling for fetch failures
    - _Requirements: 2.1, 2.2, 3.4, 6.1_

  - [ ]* 5.2 Add retry logic and request timeout to API client
    - Implement exponential backoff retry (max 3 attempts) for transient failures (5xx, network errors)
    - Add configurable request timeout (default 10s for data, 30s for Bedrock insights)
    - Add request cancellation via AbortController when component unmounts
    - _Production: Resilience and user experience_

  - [x] 5.3 Create formatter utility functions
    - Create `frontend/src/utils/formatters.js`
    - Implement `formatCurrency(value)`: Format number as GBP with thousand separators (e.g., £2,450,000)
    - Implement `formatPercentage(value)`: Format number with % suffix and appropriate decimal places
    - Implement `formatDate(dateString)`: Format ISO date string to readable format (e.g., "15 Mar 2026")
    - _Requirements: 1.4, 4.2_

  - [x] 5.4 Create risk calculation utility functions
    - Create `frontend/src/utils/riskCalculations.js`
    - Define target allocations per risk profile (Conservative, Balanced, Growth)
    - Define volatility targets per risk profile (Conservative: 8, Balanced: 12, Growth: 18)
    - Implement `computeRiskAlerts(clients, portfolios)`: Evaluate all portfolios against thresholds, return array of risk alert objects for equity overweight (>10pp over target) and volatility breach conditions
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [x] 6. Implement frontend components - Layout and Navigation
  - [x] 6.1 Implement the App component with state management and routing
    - Create `frontend/src/App.js`
    - Use Cloudscape `AppLayout` as the top-level layout with `TopNavigation` for the header
    - Manage state: clients, selectedClientId, portfolio, insights, insightsLoading, insightsError, alerts
    - Fetch clients on mount, compute risk alerts when portfolio data available
    - Render RiskAlertsBanner (Cloudscape `Flashbar`), and conditionally render ClientListView or PortfolioDetailView based on selectedClientId
    - Import `@cloudscape-design/global-styles/index.css` in the entry point
    - _Requirements: 1.1, 1.3, 7.4_

  - [ ]* 6.2 Add React Error Boundary for graceful failure handling
    - Create `frontend/src/components/ErrorBoundary.js`
    - Catch rendering errors and display a user-friendly fallback UI
    - Log error details to console (or external service in production)
    - Include a "Retry" button to reset the error state
    - _Production: Resilience and user experience_

  - [x] 6.3 Implement the Header component
    - Create `frontend/src/components/Header.js`
    - Use Cloudscape `TopNavigation` component with title "🏦 Wealth Management" and subtitle "Portfolio Risk Dashboard"
    - Apply Navy Blue (#1B365D) as the identity background colour via Cloudscape theming/CSS override
    - _Requirements: 8.1, 8.5_

  - [x] 6.4 Implement the RiskAlertsBanner component
    - Create `frontend/src/components/RiskAlertsBanner.js`
    - Accept `alerts` prop (array of risk alert objects)
    - Use Cloudscape `Flashbar` component with type "warning" for each alert
    - Display at top of page below Header within the AppLayout notifications slot
    - Return null when no alerts exist
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7. Implement frontend components - Client List
  - [x] 7.1 Implement the ClientListView component
    - Create `frontend/src/components/ClientListView.js`
    - Accept `clients` and `onSelectClient` props
    - Use Cloudscape `Table` component with column definitions for: Client Name, Portfolio Value, Risk Profile, Last Review Date
    - Format portfolio values as GBP currency with thousand separators using formatCurrency utility
    - Display risk profile using Cloudscape `Badge` or `StatusIndicator` component
    - Use Cloudscape `Link` component in the name column to make rows clickable, calling onSelectClient with the client ID
    - Wrap in Cloudscape `Container` with `Header` showing "Client Portfolios"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 8. Implement frontend components - Portfolio Detail View
  - [x] 8.1 Implement the PortfolioDetailView component
    - Create `frontend/src/components/PortfolioDetailView.js`
    - Accept `clientId` prop
    - Fetch portfolio data on mount/clientId change using the API client
    - Use Cloudscape `ContentLayout` with `Header` showing client name
    - Use Cloudscape `BreadcrumbGroup` for "Clients > {Client Name}" navigation
    - Use Cloudscape `SpaceBetween` and `Grid`/`ColumnLayout` to arrange AllocationChart, HoldingsTable, RiskMetricsPanel, and AIInsightsPanel
    - _Requirements: 3.1, 3.4, 4.1, 5.1_

  - [x] 8.2 Implement the AllocationChart component with Cloudscape PieChart
    - Create `frontend/src/components/AllocationChart.js`
    - Accept `allocation` prop
    - Use Cloudscape `PieChart` component showing 5 segments: UK Equities, International Equities, Fixed Income, Alternatives, Cash
    - Configure `detailPopoverContent` to show percentage and value details on hover
    - Use distinct segment colours for each asset class
    - Wrap in Cloudscape `Container` with `Header` showing "Asset Allocation"
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 8.3 Implement the HoldingsTable component
    - Create `frontend/src/components/HoldingsTable.js`
    - Accept `holdings` prop
    - Use Cloudscape `Table` component with column definitions for: Name, Sector, Value (GBP), Weight (%), 1M Change (%)
    - Sort holdings by weight in descending order using Cloudscape Table's `sortingColumn` prop
    - Display positive changes with Cloudscape `StatusIndicator` type="success" and negative with type="error"
    - Format values as GBP currency and percentages appropriately
    - Wrap in Cloudscape `Container` with `Header` showing "Top Holdings"
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 8.4 Implement the RiskMetricsPanel component
    - Create `frontend/src/components/RiskMetricsPanel.js`
    - Accept `metrics` prop
    - Use Cloudscape `ColumnLayout` with 4 columns, each containing a Cloudscape `Container` or `Box`
    - Display: Volatility (annualised %), Sharpe Ratio (decimal), Max Drawdown (negative %), Beta vs FTSE 100 (decimal)
    - Use Cloudscape `Box` with variant="h3" for metric labels and variant="p" for values
    - Wrap in Cloudscape `Container` with `Header` showing "Risk Metrics"
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 8.5 Implement the AIInsightsPanel component
    - Create `frontend/src/components/AIInsightsPanel.js`
    - Accept `clientId`, `allocation`, `riskProfile` props
    - Use Cloudscape `Button` variant="primary" for "Get AI Insights" action
    - Use Cloudscape `Spinner` while Bedrock is processing
    - On success, render InsightCard components for each suggestion using Cloudscape `Cards` or individual `Container` components
    - On error, display Cloudscape `Alert` with type="error" and user-friendly message
    - Wrap in Cloudscape `Container` with `Header` showing "AI Rebalancing Insights"
    - _Requirements: 6.1, 6.3, 6.4, 6.5_

  - [x] 8.6 Implement the InsightCard component
    - Create `frontend/src/components/InsightCard.js`
    - Accept `suggestion` and `index` props
    - Use Cloudscape `Container` with `Header` showing "Suggestion {index + 1}"
    - Display suggestion text using Cloudscape `Box` component
    - Use Gold (#B8860B) accent via CSS override on the container border-left
    - _Requirements: 6.3, 8.2_

- [x] 9. Checkpoint - Ensure frontend compiles and renders correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Apply branding and styling
  - [x] 10.1 Apply Cloudscape theming and custom CSS overrides
    - Create `frontend/src/index.css` with minimal CSS overrides for Wealth Management branding: Navy Blue (#1B365D) for TopNavigation background, Gold (#B8860B) for primary button accents
    - Import `@cloudscape-design/global-styles/index.css` in the entry point
    - Use Cloudscape's built-in spacing, typography, and colour tokens where possible
    - Only override where branding requires deviation from Cloudscape defaults
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ] 10.2 Add responsive layout for tablet and mobile
    - Cloudscape components are responsive by default; verify layout on smaller viewports
    - Adjust `ColumnLayout` columns prop for narrower screens if needed
    - Test `Table` horizontal scrolling on mobile
    - _Production: Accessibility across devices_

- [x] 11. Configure deployment
  - [x] 11.1 Configure Serverless Framework deployment
    - Ensure `backend/serverless.yml` has correct provider configuration: runtime nodejs22.x, region eu-west-1, stage dev
    - Each function defined separately with its own `httpApi` event — no monolithic handler, no raw CloudFormation for API Gateway
    - Add IAM role statements for Bedrock InvokeModel permission (resource: `arn:aws:bedrock:eu-west-1:*:model/eu.anthropic.claude-sonnet-4-6`)
    - Add IAM role statements for DynamoDB read/write on the ClientPortfolios table
    - No explicit credentials in code — Lambda uses instance profile automatically
    - CORS handled automatically by Serverless Framework httpApi defaults
    - _Requirements: 9.2, 9.3, 9.4_

  - [x] 11.2 Configure AWS Amplify deployment
    - Create `frontend/amplify.yml` with build settings: preBuild (npm ci), build (npm run build), baseDirectory (build)
    - Add environment variable configuration for `REACT_APP_API_URL` pointing to the API Gateway endpoint
    - Ensure the build output directory matches Create React App defaults
    - _Requirements: 9.1, 9.3_

  - [ ]* 11.3 Add Cognito authentication for API protection
    - Create a Cognito User Pool in serverless.yml resources
    - Add a Cognito authorizer to API Gateway endpoints
    - Add login/signup flow to the frontend using AWS Amplify Auth library
    - Protect all API routes behind JWT token validation
    - _Production: Authentication and access control_

  - [ ]* 11.4 Add CloudWatch alarms and X-Ray tracing
    - Enable X-Ray tracing on the Lambda function in serverless.yml
    - Create CloudWatch alarms for: Lambda errors > 5 in 5 minutes, Lambda duration > 10s, API Gateway 5xx > 10 in 5 minutes
    - Add an SNS topic for alarm notifications
    - _Production: Monitoring and alerting_

  - [ ]* 11.5 Add WAF rules to API Gateway
    - Create a WAF WebACL with rate limiting (1000 requests per IP per 5 minutes)
    - Attach WAF to the API Gateway stage
    - Add AWS managed rule groups for common threats (SQL injection, XSS)
    - _Production: API security and DDoS protection_

  - [ ]* 11.6 Configure CI/CD pipeline
    - Create GitHub Actions workflow for automated deployment
    - Add stages: lint → test → build → deploy-backend → seed-data → deploy-frontend
    - Add environment separation (dev, staging, prod) via Serverless Framework stages
    - Run integration tests against deployed API before promoting to production
    - _Production: Automated deployment and environment management_

- [x] 12. Final checkpoint - Ensure all code compiles and integrates correctly
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All code is plain JavaScript (no TypeScript) — both frontend and backend
- Tasks marked with `*` are optional and can be skipped for faster MVP delivery, but are recommended for production readiness
- The backend uses individual Lambda functions per endpoint (one function per httpApi event in serverless.yml) — no monolithic handler
- Client and portfolio data is stored in a single DynamoDB table (`ClientPortfolios`) using PK/SK single-table design and seeded via a script
- The frontend uses Cloudscape Design System components for UI (not custom CSS-only styling)
- Risk alerts are computed client-side from portfolio data already fetched
- The API base URL is configurable via environment variable for easy switching between local and deployed environments
- CORS is handled automatically by Serverless Framework httpApi defaults; production should restrict to the Amplify domain
- Authentication (Cognito) is optional for the demo but strongly recommended for any customer-facing deployment
