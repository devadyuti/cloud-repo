# Requirements Document

## Introduction

The Client Portfolio Risk Dashboard is a lightweight single-page application for Wealth Management investment managers. It enables managers to view client portfolio allocations, assess risk exposure through key metrics and visual charts, and receive AI-generated rebalancing suggestions powered by Amazon Bedrock. The application uses React 18 for the frontend, AWS Lambda (Node.js 22) for the backend API, and mock JSON data for the demo scope.

## Glossary

- **Dashboard**: The React 18 single-page application that renders client portfolios, risk metrics, and AI insights
- **API_Gateway**: The AWS API Gateway REST service that routes HTTP requests to Lambda functions
- **Lambda_Service**: The AWS Lambda (Node.js 22) backend functions that serve client and portfolio data
- **Bedrock_Service**: The Amazon Bedrock (Claude) integration that generates AI rebalancing suggestions
- **Client_List_View**: The page component displaying all mock clients in a tabular format
- **Portfolio_Detail_View**: The page component displaying a single client's allocation chart, holdings table, and risk metrics
- **Allocation_Chart**: The pie chart component visualising asset class breakdown (UK Equities, International Equities, Fixed Income, Alternatives, Cash)
- **Holdings_Table**: The table component displaying a client's top 10 holdings with name, sector, value, weight, and 1-month change
- **Risk_Metrics_Panel**: The panel component displaying portfolio volatility, Sharpe ratio, max drawdown, and beta vs FTSE 100
- **Risk_Alerts_Banner**: The top-of-page banner component displaying warnings for portfolios breaching risk thresholds
- **AI_Insights_Panel**: The card layout component displaying AI-generated rebalancing suggestions
- **Investment_Manager**: A wealth management professional who uses the Dashboard to monitor client portfolios

## Requirements

### Requirement 1: Display Client List

**User Story:** As an Investment Manager, I want to see a list of all my clients with key summary information, so that I can quickly identify which client portfolio to review.

#### Acceptance Criteria

1. WHEN the Dashboard loads, THE Client_List_View SHALL display all clients from the mock data source
2. THE Client_List_View SHALL display each client's name, total portfolio value, risk profile, and last review date
3. WHEN an Investment Manager clicks a client row, THE Dashboard SHALL navigate to the Portfolio_Detail_View for that client
4. THE Client_List_View SHALL format portfolio values as GBP currency with appropriate thousand separators
5. THE Client_List_View SHALL display the risk profile as one of: Conservative, Balanced, or Growth

### Requirement 2: Retrieve Client Data via API

**User Story:** As an Investment Manager, I want the dashboard to fetch client data from a backend API, so that the frontend remains decoupled from the data source.

#### Acceptance Criteria

1. WHEN the Dashboard requests the client list, THE API_Gateway SHALL respond to GET /clients with a JSON array of all client records
2. WHEN the Dashboard requests a specific client, THE API_Gateway SHALL respond to GET /clients/{id} with the matching client record
3. IF a requested client ID does not exist, THEN THE Lambda_Service SHALL return an HTTP 404 response with a descriptive error message
4. THE Lambda_Service SHALL return client records containing: id, name, portfolioValue, riskProfile, lastReviewDate, and investmentManager fields

### Requirement 3: Display Portfolio Allocation Chart

**User Story:** As an Investment Manager, I want to see a visual breakdown of a client's asset allocation, so that I can quickly assess diversification.

#### Acceptance Criteria

1. WHEN the Portfolio_Detail_View loads for a client, THE Allocation_Chart SHALL render a pie chart showing the percentage allocation across asset classes
2. THE Allocation_Chart SHALL display the following asset classes: UK Equities, International Equities, Fixed Income, Alternatives, and Cash
3. THE Allocation_Chart SHALL display percentage labels for each segment
4. WHEN the Dashboard requests portfolio data, THE API_Gateway SHALL respond to GET /clients/{id}/portfolio with the allocation and holdings data

### Requirement 4: Display Holdings Table

**User Story:** As an Investment Manager, I want to see a detailed table of a client's top holdings, so that I can review individual position performance.

#### Acceptance Criteria

1. WHEN the Portfolio_Detail_View loads for a client, THE Holdings_Table SHALL display up to 10 holdings
2. THE Holdings_Table SHALL display each holding's name, sector, value (GBP formatted), weight percentage, and 1-month change percentage
3. THE Holdings_Table SHALL display positive 1-month changes with a green indicator and negative changes with a red indicator
4. THE Holdings_Table SHALL sort holdings by weight in descending order

### Requirement 5: Display Risk Metrics

**User Story:** As an Investment Manager, I want to see key risk metrics for a client's portfolio, so that I can assess whether the portfolio is within acceptable risk parameters.

#### Acceptance Criteria

1. WHEN the Portfolio_Detail_View loads for a client, THE Risk_Metrics_Panel SHALL display portfolio volatility as an annualised percentage
2. THE Risk_Metrics_Panel SHALL display the Sharpe ratio as a decimal value
3. THE Risk_Metrics_Panel SHALL display the maximum drawdown over 12 months as a negative percentage
4. THE Risk_Metrics_Panel SHALL display beta versus FTSE 100 as a decimal value

### Requirement 6: Generate AI Rebalancing Suggestions

**User Story:** As an Investment Manager, I want to receive AI-generated rebalancing suggestions for a client's portfolio, so that I can identify actionable improvements to portfolio composition.

#### Acceptance Criteria

1. WHEN an Investment Manager clicks the "Get AI Insights" button, THE Dashboard SHALL send a POST request to /clients/{id}/insights with the current allocation and risk profile
2. WHEN the Bedrock_Service receives a valid insights request, THE Bedrock_Service SHALL return between 3 and 4 actionable rebalancing suggestions
3. THE AI_Insights_Panel SHALL display each suggestion in a styled card layout
4. WHILE the Bedrock_Service is processing a request, THE Dashboard SHALL display a loading indicator
5. IF the Bedrock_Service returns an error, THEN THE Dashboard SHALL display a user-friendly error message in the AI_Insights_Panel
6. THE Bedrock_Service SHALL include specific percentage values and asset class references in each suggestion

### Requirement 7: Display Risk Alerts

**User Story:** As an Investment Manager, I want to see prominent alerts when client portfolios breach risk thresholds, so that I can prioritise portfolios requiring immediate attention.

#### Acceptance Criteria

1. WHEN the Dashboard loads, THE Risk_Alerts_Banner SHALL evaluate all client portfolios against risk thresholds
2. WHEN a client's equity allocation exceeds the target allocation by more than 10 percentage points, THE Risk_Alerts_Banner SHALL display a warning identifying the client
3. WHEN a client's portfolio volatility exceeds the target for their risk profile, THE Risk_Alerts_Banner SHALL display a warning identifying the client and the metric
4. THE Risk_Alerts_Banner SHALL display at the top of the page above the Client_List_View
5. IF no portfolios breach risk thresholds, THEN THE Risk_Alerts_Banner SHALL not be visible

### Requirement 8: Apply Wealth Management Branding

**User Story:** As an Investment Manager, I want the dashboard to reflect professional wealth management branding, so that the tool feels consistent with the firm's identity.

#### Acceptance Criteria

1. THE Dashboard SHALL use Navy Blue (#1B365D) as the primary colour for headers and navigation
2. THE Dashboard SHALL use Gold (#B8860B) as the secondary colour for accents and interactive elements
3. THE Dashboard SHALL use Light Grey (#F5F5F5) as the background colour for content areas
4. THE Dashboard SHALL use the Inter font family for all text elements
5. THE Dashboard SHALL display "🏦 Wealth Management" as the application title in the header

### Requirement 9: Deploy to AWS Infrastructure

**User Story:** As an Investment Manager, I want the dashboard to be accessible via a web URL, so that I can access it from any browser without local setup.

#### Acceptance Criteria

1. THE Dashboard SHALL be deployed as a static site via AWS Amplify
2. THE Lambda_Service SHALL be deployed via Serverless Framework 4 to the eu-west-1 AWS region
3. THE API_Gateway SHALL expose REST endpoints accessible from the Amplify-hosted frontend
4. THE API_Gateway SHALL enable CORS to allow requests from the Amplify domain

### Requirement 10: Serve Mock Data from Lambda

**User Story:** As an Investment Manager, I want the dashboard to display realistic portfolio data, so that I can evaluate the tool's usefulness with representative scenarios.

#### Acceptance Criteria

1. THE Lambda_Service SHALL serve data for 5 mock clients with distinct risk profiles and portfolio values
2. THE Lambda_Service SHALL serve portfolio data including allocation percentages, top 10 holdings, and risk metrics for each client
3. THE Lambda_Service SHALL return consistent data across repeated requests for the same client
