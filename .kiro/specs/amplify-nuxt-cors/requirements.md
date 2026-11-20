# Requirements Document

## Introduction

This document defines the requirements for building a minimal Nuxt.js 3 SSG sample application that reproduces the exact issues experienced by AnyCompany on AWS Amplify Hosting. The reproduction app serves as a diagnostic tool to confirm root causes, test potential fixes in isolation, and develop a proven solution before applying changes to the customer's production site (anycompany.com). The issues include direct URL 404 errors, SPA rewrite rule conflicts, CORS errors from Sanity.io CMS API calls, trailing slash route failures, and all-routes-redirect-to-home behavior — all traced to AWS Amplify's default rewrite/redirect rules being incompatible with Nuxt SSG output (documented in aws-amplify/amplify-hosting#3829).

## Glossary

- **Repro_App**: The minimal Nuxt.js 3 application configured in Static Site Generation mode, built specifically to reproduce the AnyCompany production issues on AWS Amplify Hosting.
- **Amplify_Hosting**: The AWS Amplify Hosting service responsible for deploying, serving, and managing rewrite/redirect rules for the Repro_App.
- **Nuxt_SSG_Build**: The Nuxt.js static site generation build output produced by `nuxt generate`, which creates pre-rendered HTML files for each route rather than a single `index.html` SPA entry point.
- **SPA_Catch_All_Rule**: The default Amplify rewrite rule (`</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>` → `/index.html` with 200 status) that redirects all unmatched routes to `/index.html`, designed for SPAs but incompatible with Nuxt SSG output.
- **Sanity_API_Mock**: A component within the Repro_App that simulates client-side API calls to a Sanity.io CMS endpoint (your-project-id.apicdn.sanity.io) to reproduce CORS error conditions.
- **Route_Test_Suite**: The set of application routes within the Repro_App designed to exercise direct URL access, trailing slash behavior, client-side navigation, and nested route resolution.
- **Diagnostic_Dashboard**: A page within the Repro_App that displays the results of automated route and CORS checks, providing a visual summary of which issues are reproduced.
- **Amplify_Build_Spec**: The `amplify.yml` configuration file that defines build commands, artifact paths, and custom headers for the Amplify deployment of the Repro_App.
- **Trailing_Slash_Route**: A URL path that ends with a forward slash character (e.g., `/valuation/`).
- **Fix_Mode_Toggle**: A configuration mechanism within the Repro_App that allows switching between the broken default Amplify configuration and a proposed fix configuration, enabling A/B comparison of behavior.

## Requirements

### Requirement 1: Nuxt 3 SSG Application Scaffold

**User Story:** As a support engineer, I want a minimal Nuxt.js 3 application configured for Static Site Generation, so that the build output matches the structure that causes issues on Amplify Hosting.

#### Acceptance Criteria

1. THE Repro_App SHALL use Nuxt.js version 3 with the `nuxt generate` command to produce a Nuxt_SSG_Build output.
2. THE Repro_App SHALL include a `nuxt.config.ts` file with `ssr: true` and the `nitro.preset` set to `static` to match the AnyCompany production configuration.
3. WHEN `nuxt generate` is executed, THE Nuxt_SSG_Build SHALL produce pre-rendered HTML files for each defined route in the application.
4. THE Repro_App SHALL include a `package.json` with build scripts for `generate` (static build) and `dev` (local development).

### Requirement 2: Multi-Route Page Structure

**User Story:** As a support engineer, I want the reproduction app to include multiple routes that mirror the AnyCompany site structure, so that I can test direct URL access, client-side navigation, and nested route behavior.

#### Acceptance Criteria

1. THE Repro_App SHALL include the following top-level routes: `/` (home), `/valuation`, `/login`, `/about`, and `/contact`.
2. THE Repro_App SHALL include at least one nested route structure (e.g., `/blog/post-1`, `/blog/post-2`) to test nested path resolution.
3. WHEN a route page is rendered, THE Repro_App SHALL display the current route path, the page title, and a navigation menu linking to all other routes.
4. THE Repro_App SHALL include client-side navigation links (using `<NuxtLink>`) between all pages to verify that client-side routing works independently of server-side route resolution.
5. WHEN the Nuxt_SSG_Build is generated, THE Repro_App SHALL produce a pre-rendered HTML file for each route defined in the Route_Test_Suite.

### Requirement 3: Sanity.io CMS API Call Simulation

**User Story:** As a support engineer, I want the reproduction app to make client-side API calls to a Sanity.io endpoint, so that I can reproduce the CORS errors seen in the AnyCompany production environment.

#### Acceptance Criteria

1. THE Repro_App SHALL include a page or component that makes a client-side HTTP GET request to `https://your-project-id.apicdn.sanity.io` (or a configurable Sanity project endpoint) on page load.
2. WHEN the client-side request to the Sanity_API_Mock endpoint is blocked by CORS policy, THE Repro_App SHALL capture the error and display the CORS error message on the Diagnostic_Dashboard.
3. THE Repro_App SHALL allow the Sanity API endpoint URL to be configured via an environment variable (`NUXT_PUBLIC_SANITY_API_URL`) so that the endpoint can be changed without modifying source code.
4. IF the Sanity API endpoint is unreachable or returns a CORS error, THEN THE Repro_App SHALL display the HTTP status code, the error type (CORS, network, timeout), and the request URL on the page.

### Requirement 4: Amplify Hosting Deployment Configuration

**User Story:** As a support engineer, I want the reproduction app to include an Amplify build specification that replicates the default Amplify configuration causing issues, so that the deployment reproduces the exact broken behavior.

#### Acceptance Criteria

1. THE Amplify_Build_Spec SHALL define the build command as `npm run generate` and the artifact base directory as `.output/public` (or the correct Nuxt 3 SSG output directory).
2. THE Amplify_Build_Spec SHALL include the default SPA_Catch_All_Rule (`</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>` → `/index.html` with 200 status) in the rewrite rules section to reproduce the broken behavior.
3. THE Amplify_Build_Spec SHALL specify Node.js version 18 or later as the build environment runtime.
4. WHEN the Repro_App is deployed to Amplify_Hosting using the Amplify_Build_Spec, THE Amplify_Hosting SHALL apply the defined rewrite rules to all incoming requests.

### Requirement 5: Direct URL Access 404 Reproduction

**User Story:** As a support engineer, I want to confirm that direct URL access to routes like `/valuation` returns a 404 error on Amplify, so that I can verify this matches the customer's reported behavior.

#### Acceptance Criteria

1. WHEN a user navigates directly to `/valuation` (via browser address bar or external link) on the deployed Repro_App, THE Amplify_Hosting SHALL return either a 404 error or redirect to the home page, reproducing the reported broken behavior.
2. WHEN a user navigates to `/valuation/index.html` on the deployed Repro_App, THE Amplify_Hosting SHALL return the correct page content with an HTTP 200 status, confirming the index.html suffix workaround.
3. WHEN a user navigates to `/valuation` via client-side navigation (clicking a NuxtLink from another page), THE Repro_App SHALL render the correct page content without errors, confirming client-side routing is unaffected.
4. THE Diagnostic_Dashboard SHALL test each route in the Route_Test_Suite via `fetch()` and report the HTTP status code for both direct access (without `/index.html`) and with the `/index.html` suffix.

### Requirement 6: Trailing Slash Route Failure Reproduction

**User Story:** As a support engineer, I want to confirm that routes with trailing slashes fail on the deployed app, so that I can verify this matches the customer's reported trailing slash issues.

#### Acceptance Criteria

1. WHEN a user navigates directly to a Trailing_Slash_Route (e.g., `/valuation/`) on the deployed Repro_App, THE Amplify_Hosting SHALL return a 404 error or redirect to the home page, reproducing the reported broken behavior.
2. WHEN a user navigates directly to the same route without a trailing slash (e.g., `/valuation`), THE Repro_App SHALL exhibit the same direct URL 404 behavior described in Requirement 5.
3. THE Diagnostic_Dashboard SHALL test each route in the Route_Test_Suite with and without trailing slashes and report the HTTP status code for each variant.

### Requirement 7: All-Routes-Redirect-to-Home Reproduction

**User Story:** As a support engineer, I want to confirm that the SPA catch-all rule causes all routes to serve the home page content instead of the correct page, so that I can verify this specific symptom.

#### Acceptance Criteria

1. WHEN the SPA_Catch_All_Rule is active and a user navigates directly to any non-home route (e.g., `/about`), THE Amplify_Hosting SHALL serve the `/index.html` content (home page) instead of the route-specific content.
2. THE Diagnostic_Dashboard SHALL compare the HTML content returned for each route against the expected page title and report whether the correct page or the home page was served.
3. WHEN the SPA_Catch_All_Rule is active, THE Repro_App SHALL demonstrate that the browser URL shows the requested path (e.g., `/about`) while the rendered content is the home page.

### Requirement 8: Diagnostic Dashboard

**User Story:** As a support engineer, I want a built-in diagnostic page that automatically tests all known issue scenarios and displays results, so that I can quickly verify which issues are reproduced and which fixes are effective.

#### Acceptance Criteria

1. THE Repro_App SHALL include a `/diagnostics` route that displays the Diagnostic_Dashboard.
2. WHEN the Diagnostic_Dashboard is loaded, THE Repro_App SHALL execute automated checks for: direct URL access (each route), trailing slash access (each route), CORS request to the Sanity API endpoint, and content verification (correct page vs. home page redirect).
3. THE Diagnostic_Dashboard SHALL display each test result with a status indicator (pass, fail, error), the HTTP status code, and a description of the expected vs. actual behavior.
4. THE Diagnostic_Dashboard SHALL display the current Amplify deployment URL, the Nuxt build mode, and the active rewrite rule configuration for context.
5. WHEN all diagnostic checks are complete, THE Diagnostic_Dashboard SHALL display a summary count of passed, failed, and errored tests.

### Requirement 9: Fix Mode Configuration Toggle

**User Story:** As a support engineer, I want to toggle between the broken default configuration and a proposed fix configuration, so that I can compare behavior and validate that a fix resolves each issue.

#### Acceptance Criteria

1. THE Repro_App SHALL support a Fix_Mode_Toggle that switches the Amplify rewrite rules between the default broken configuration (with SPA_Catch_All_Rule) and a proposed fix configuration (with SSG-compatible rules).
2. THE Fix_Mode_Toggle SHALL be implemented as separate Amplify build spec files (e.g., `amplify.yml` for broken mode, `amplify-fix.yml` for fix mode) that can be swapped before deployment.
3. WHEN the fix configuration is active, THE Amplify_Build_Spec SHALL remove the SPA_Catch_All_Rule and replace it with rules that serve pre-rendered HTML files directly for each route.
4. THE Repro_App README SHALL document the steps to switch between broken and fix configurations and redeploy.

### Requirement 10: Documentation and Reproduction Steps

**User Story:** As a support engineer, I want clear documentation explaining how to deploy the reproduction app and verify each issue, so that any team member can use the app to diagnose and test fixes.

#### Acceptance Criteria

1. THE Repro_App SHALL include a README.md file that documents: the purpose of the reproduction app, prerequisites (Node.js, AWS account, Amplify CLI), setup and deployment steps, how to run the diagnostic dashboard, and how to switch between broken and fix configurations.
2. THE README.md SHALL include a reference to the known bug (aws-amplify/amplify-hosting#3829) and a summary of the customer's reported issues.
3. THE README.md SHALL include a table mapping each reproduced issue to the corresponding diagnostic test and the proposed fix approach.
4. THE README.md SHALL document the list of attempted fixes that failed (CORS header updates, Amplify reverse proxy, removing SPA rewrite rule, Nuxt config changes, redirect/rewrite pattern matching) with a brief explanation of why each failed.
