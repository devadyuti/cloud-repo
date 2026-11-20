# Implementation Plan: Amplify Nuxt CORS

## Overview

Build a minimal Nuxt 3 SSG application that reproduces AnyCompany's AWS Amplify Hosting issues (direct URL 404s, SPA rewrite conflicts, CORS errors, trailing slash failures, all-routes-redirect-to-home). The app includes a diagnostic dashboard, dual Amplify build specs for A/B comparison, and a Nuxt server route for Sanity.io CMS proxying. All code is JavaScript only, targeting Node.js 22 and eu-west-1.

## Tasks

- [x] 1. Scaffold Nuxt 3 project and core configuration
  - [x] 1.1 Initialize `amplify-nuxt-cors/` with `package.json` including `dev`, `generate`, and `preview` scripts, Nuxt 3 dependency, and Node.js 22 engine field
    - _Requirements: 1.1, 1.4_
  - [x] 1.2 Create `nuxt.config.js` with `ssr: true`, `nitro.preset: 'static'`, runtime config for `sanityApiUrl` and `public.sanityApiUrl` (from env vars), and app head metadata
    - _Requirements: 1.2, 3.3_
  - [x] 1.3 Create `.env.example` with `NUXT_PUBLIC_SANITY_API_URL` and `NUXT_SANITY_API_URL` entries
    - _Requirements: 3.3_
  - [x] 1.4 Create `public/favicon.ico` placeholder
    - _Requirements: 1.1_

- [x] 2. Build navigation and page structure
  - [x] 2.1 Create `components/NavBar.vue` with `NuxtLink` elements for all routes (`/`, `/valuation`, `/login`, `/about`, `/contact`, `/blog`, `/diagnostics`) and active route highlighting via `useRoute()`
    - _Requirements: 2.3, 2.4_
  - [x] 2.2 Create `app.vue` root shell that includes the `NavBar` component and `<NuxtPage />`
    - _Requirements: 2.3_
  - [x] 2.3 Create page components: `pages/index.vue`, `pages/valuation.vue`, `pages/login.vue`, `pages/about.vue`, `pages/contact.vue` — each displaying a unique page title, current route path from `useRoute().path`, and the NavBar
    - _Requirements: 2.1, 2.3, 2.4, 2.5_
  - [x] 2.4 Create nested blog pages: `pages/blog/index.vue`, `pages/blog/post-1.vue`, `pages/blog/post-2.vue` — each with unique title and route path display
    - _Requirements: 2.2, 2.3, 2.5_

- [x] 3. Implement Sanity.io CMS proxy and client composables
  - [x] 3.1 Create `server/api/sanity.js` — GET handler that reads `query` param, fetches from Sanity API URL (from runtime config) server-side, returns JSON or error `{ error: true, status, message }`; returns 400 if `query` is missing
    - _Requirements: 3.1, 3.3_
  - [x] 3.2 Create `composables/useSanity.js` returning `fetchDirect(query)` (client-side fetch to Sanity API URL, triggers CORS) and `fetchProxy(query)` (fetch to `/api/sanity`); classify errors as `cors`, `network`, `timeout` (5s AbortController), or `http`
    - _Requirements: 3.1, 3.2, 3.4_
  - [x] 3.3 Create `components/SanityDemo.vue` accepting `mode` prop (`'direct'` or `'proxy'`), calling the corresponding `useSanity` method on mount, displaying result data or full error details (status, type, URL)
    - _Requirements: 3.1, 3.2, 3.4_

- [x] 4. Implement route test definitions and diagnostic composables
  - [x] 4.1 Create `composables/useRouteTests.js` returning `routes` array with all route paths and expected page titles (e.g., `{ path: '/valuation', title: 'Valuation' }`)
    - _Requirements: 5.4, 6.3, 7.2_
  - [x] 4.2 Create `composables/useDiagnostics.js` returning `{ results, summary, runAll, isRunning }` — `runAll()` executes checks for: direct URL access per route, trailing slash per route, CORS request to Sanity, and content verification (expected title vs. home page title); `summary` computes passed/failed/errored counts
    - _Requirements: 5.4, 6.3, 7.2, 8.2, 8.5_

- [x] 5. Build diagnostic dashboard UI
  - [x] 5.1 Create `components/TestResultCard.vue` displaying status indicator (✅/❌/⚠️), test name, category, HTTP status code, expected vs. actual behavior, and tested URL
    - _Requirements: 8.3_
  - [x] 5.2 Create `components/DiagnosticRunner.vue` that calls `useDiagnostics().runAll()` on mount, displays context info (deployment URL, build mode, rewrite config), renders `TestResultCard` for each result, and shows summary counts
    - _Requirements: 8.2, 8.3, 8.4, 8.5_
  - [x] 5.3 Create `pages/diagnostics.vue` that renders `SanityDemo` (both direct and proxy modes) and `DiagnosticRunner`
    - _Requirements: 8.1, 8.2, 3.2_

- [x] 6. Checkpoint — Verify local dev works
  - Ensure `npm install` and `npm run dev` succeed locally, all pages render at their routes, NavBar links work, `/diagnostics` loads and runs checks, and the Sanity direct call shows a CORS error while the proxy call succeeds. Ask the user if questions arise.

- [x] 7. Create Amplify build specs
  - [x] 7.1 Create `amplify.yml` (broken mode) with `nvm use 22`, `npm ci`, `npm run generate`, artifact base `.output/public`, custom header `X-Repro-Mode: broken`, and the SPA catch-all rewrite rule (`</^[^.]+$|.../>` → `/index.html` 200)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 9.1_
  - [x] 7.2 Create `amplify-fix.yml` (fix mode) with same build commands but no SPA catch-all rewrite, custom header `X-Repro-Mode: fixed`, and `Cache-Control` header
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 8. Write README and documentation
  - [x] 8.1 Create `README.md` with: purpose and background (reference aws-amplify/amplify-hosting#3829), prerequisites (Node.js 22, AWS account, Amplify), quick start (clone, install, `npm run dev`, visit `/diagnostics`), deploy to Amplify steps (eu-west-1), issue reproduction table mapping each issue to diagnostic test and expected result
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 8.2 Add fix mode section to README: steps to copy `amplify-fix.yml` → `amplify.yml`, redeploy, and verify fixes on `/diagnostics`
    - _Requirements: 9.4, 10.1_
  - [x] 8.3 Add failed fix attempts section to README documenting: CORS header updates, Amplify reverse proxy, removing SPA rewrite only, Nuxt config changes, redirect/rewrite pattern matching — with brief explanation of why each failed
    - _Requirements: 10.4_

- [x] 9. Checkpoint — Verify SSG build output
  - Run `npm run generate` and verify `.output/public/` contains per-route `index.html` files (e.g., `valuation/index.html`, `blog/post-1/index.html`). Ensure all tests pass, ask the user if questions arise.

- [x] 10. Property-based and unit tests
  - [ ]* 10.1 Set up Vitest and fast-check as dev dependencies in `package.json`, add `test` script
    - _Requirements: 1.4_
  - [ ]* 10.2 Write property test for Property 1: Page rendering includes route path, title, and navigation
    - **Property 1: Page rendering includes route path, title, and navigation**
    - Generate random subsets of the route list, verify rendered output contains path, title, and nav links
    - **Validates: Requirements 2.3, 2.4**
  - [ ]* 10.3 Write property test for Property 2: Error display includes all diagnostic fields
    - **Property 2: Error display includes all diagnostic fields**
    - Generate random SanityError objects, verify error display renders status, type, and URL
    - **Validates: Requirements 3.4**
  - [ ]* 10.4 Write property test for Property 3: Diagnostic check correctness across route variants
    - **Property 3: Diagnostic check correctness across route variants**
    - Generate random routes and mock HTTP responses, verify pass/fail determination, trailing-slash testing, and content verification
    - **Validates: Requirements 5.4, 6.3, 7.2**
  - [ ]* 10.5 Write property test for Property 4: Test result rendering completeness
    - **Property 4: Test result rendering completeness**
    - Generate random TestResult objects, verify rendered output contains status indicator, HTTP code, and description
    - **Validates: Requirements 8.3**
  - [ ]* 10.6 Write property test for Property 5: Summary count correctness
    - **Property 5: Summary count correctness**
    - Generate random arrays of TestResult objects, verify `passed + failed + errored === total` and each count matches
    - **Validates: Requirements 8.5**
  - [ ]* 10.7 Write unit tests for `server/api/sanity.js` — test proxy with mocked upstream responses, missing query param returns 400, upstream error returns 502
    - _Requirements: 3.1, 3.3_
  - [ ]* 10.8 Write unit tests for `useSanity.js` — test error classification (CORS TypeError, network error, timeout, HTTP error)
    - _Requirements: 3.4_
  - [ ]* 10.9 Write unit tests for `useRouteTests.js` — verify route list contains all expected routes with correct titles
    - _Requirements: 2.1, 2.2_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All file paths are relative to `amplify-nuxt-cors/`
- JavaScript only — no TypeScript; all files use `.js` or `.vue` extensions
- Node.js 22, AWS region eu-west-1
- Amplify SDK v6 for any client-side AWS service calls
- Nuxt server routes for CMS proxy (no Lambda/API Gateway)
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
