# Implementation Plan: Markdown Document Viewer

## Overview

Incremental implementation of a React SPA that fetches and renders markdown documents from S3. Starts with backend infrastructure, then builds the React app layer by layer: config, routing, document fetching, markdown rendering, error handling, and responsive styling. Each step builds on the previous and ends with full integration.

## Tasks

- [x] 1. Set up Serverless Framework V4 backend infrastructure
  - [x] 1.1 Create `serverless.yml` with S3 bucket, Cognito Identity Pool, IAM unauthenticated role, and role attachment
    - Define `DocumentBucket` S3 resource with CORS allowing GET from `https://docs.example.com`
    - Define `CognitoIdentityPool` with `AllowUnauthenticatedIdentities: true`
    - Define `UnauthenticatedRole` IAM role with `s3:GetObject` permission scoped to the bucket
    - Define `IdentityPoolRoleAttachment` to wire the role to the identity pool
    - Output bucket name, region, and identity pool ID for frontend config
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 2. Initialize React application and Amplify configuration
  - [x] 2.1 Scaffold React app with project structure and dependencies
    - Initialize with Create React App or minimal React setup (NodeJS 22, NPM 10)
    - Install dependencies: `react-router-dom`, `aws-amplify`, `react-markdown`, `remark-gfm`, `react-syntax-highlighter`
    - Install dev dependencies: `jest`, `@testing-library/react`, `@testing-library/jest-dom`, `fast-check`
    - Ensure all source files use kebab-case naming
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 2.2 Create Amplify V6 configuration module (`src/amplify-config.js`)
    - Export config object with `Storage.S3` (bucket, region) and `Auth.Cognito` (identityPoolId, allowGuestAccess)
    - Add a `validateConfig` function that checks required fields and throws descriptive errors if missing
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 Create app entry point (`src/index.js`)
    - Import and validate Amplify config
    - Call `Amplify.configure()` with the config
    - Render `<App />` into the DOM
    - If config validation fails, render an error message instead
    - _Requirements: 1.1, 1.2_

  - [ ]* 2.4 Write unit tests for Amplify config validation
    - Test `validateConfig` with missing bucket, missing region, missing identityPoolId
    - Test valid config passes without error
    - _Requirements: 1.2_

- [x] 3. Implement client-side routing
  - [x] 3.1 Create landing page component (`src/pages/landing-page.js`)
    - Simple welcome page rendered at root route `/`
    - _Requirements: 2.3_

  - [x] 3.2 Create app router (`src/app.js`)
    - Use `BrowserRouter` from `react-router-dom`
    - Route `/` to `<LandingPage />`
    - Catch-all route `/*` to `<DocumentPage />` (placeholder for now)
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

  - [ ]* 3.3 Write unit tests for routing
    - Verify `/` renders the landing page
    - Verify a document path renders the document page component
    - _Requirements: 2.3, 2.1_

- [x] 4. Implement document service and document page
  - [x] 4.1 Create document service (`src/services/document-service.js`)
    - Implement `fetchDocument(path)` that constructs S3 key as `${path}.md`
    - Use Amplify V6 Storage `downloadData()` to fetch from S3
    - Convert response body to text and return markdown string
    - Throw `DocumentNotFoundError` on 404/NoSuchKey
    - Throw `NetworkError` on network failures
    - Export helper functions `pathToS3Key(path)` and `s3KeyToPath(key)` for route-to-key mapping
    - _Requirements: 3.1, 3.2, 3.5, 2.1, 2.2, 2.5_

  - [ ]* 4.2 Write property test for route-to-S3 key mapping (Property 1)
    - **Property 1: Route-to-S3 key mapping**
    - Generate random valid URL path strings (alphanumeric segments separated by `/`)
    - Verify `pathToS3Key(path)` returns `path + ".md"`
    - Verify `s3KeyToPath(pathToS3Key(path))` returns the original path (round-trip)
    - Minimum 100 iterations with `fast-check`
    - **Validates: Requirements 2.1, 2.2, 3.1**

  - [x] 4.3 Create document page component (`src/pages/document-page.js`)
    - Extract document path from URL using `useLocation()` from React Router
    - Call `fetchDocument()` on mount and path change
    - Manage state: `{ content, loading, error }`
    - Show loading indicator while fetching
    - Show error display with retry button on error
    - Show "document not found" message for `DocumentNotFoundError`
    - Pass content to markdown renderer on success
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 2.4, 5.4_

  - [ ]* 4.4 Write unit tests for document page
    - Test loading state is displayed during fetch
    - Test "document not found" message for missing documents
    - Test error message on network failure
    - Test retry button re-triggers fetch
    - _Requirements: 3.3, 3.4, 3.5, 5.4_

- [x] 5. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement markdown rendering
  - [x] 6.1 Create markdown renderer component (`src/components/markdown-renderer.js`)
    - Use `react-markdown` with `remark-gfm` plugin for GFM support (tables, strikethrough)
    - Use `react-syntax-highlighter` with a light theme for fenced code block syntax highlighting
    - Apply consistent readable styling to rendered HTML elements
    - Accept `content` prop (string) and render as styled HTML
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 6.2 Write property test for markdown rendering robustness (Property 2)
    - **Property 2: Markdown rendering robustness**
    - Generate arbitrary strings using `fc.string()`
    - Pass each to the markdown renderer and verify it produces non-empty output without throwing
    - Minimum 100 iterations with `fast-check`
    - **Validates: Requirements 4.1, 4.6**

  - [ ]* 6.3 Write property test for syntax highlighting on fenced code blocks (Property 3)
    - **Property 3: Syntax highlighting applied to fenced code blocks**
    - Generate random code content and pick from language identifiers (javascript, python, java, etc.)
    - Construct fenced code block markdown strings
    - Verify rendered output contains syntax highlighting markup (elements with `class` or `style` attributes)
    - Minimum 100 iterations with `fast-check`
    - **Validates: Requirements 4.4**

  - [ ]* 6.4 Write unit tests for markdown rendering features
    - Test headings, paragraphs, lists, code blocks, inline code, links, images, bold, italic, blockquotes, horizontal rules
    - Test table rendering
    - Test malformed markdown renders gracefully
    - _Requirements: 4.2, 4.3, 4.6_

- [x] 7. Implement error handling components
  - [x] 7.1 Create error boundary component (`src/components/error-boundary.js`)
    - React class component with `componentDidCatch`
    - Catch unhandled errors and display user-friendly error page with reload option
    - _Requirements: 5.1_

  - [x] 7.2 Create loading indicator component (`src/components/loading-indicator.js`)
    - Simple spinner or skeleton displayed during document fetch
    - _Requirements: 3.3, 5.2_

  - [x] 7.3 Create error display component (`src/components/error-display.js`)
    - Accept `message` and optional `onRetry` props
    - Display error message and retry button when `onRetry` is provided
    - _Requirements: 3.4, 5.3, 5.4_

  - [x] 7.4 Wire error boundary into app (`src/app.js`)
    - Wrap router with `<ErrorBoundary>` in the app component
    - _Requirements: 5.1_

  - [ ]* 7.5 Write unit tests for error boundary
    - Verify error boundary catches thrown errors and renders error page
    - _Requirements: 5.1_

- [x] 8. Implement responsive layout and styling
  - [x] 8.1 Create global styles and layout (`src/styles/global.css`)
    - Constrain document content to max-width 800px, centered
    - Add responsive styles for screens narrower than 768px (adjust font sizes, padding, spacing)
    - Ensure layout adapts from 320px to 1920px
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 8.2 Write unit tests for responsive layout
    - Verify content container has max-width of 800px
    - _Requirements: 8.2_

- [x] 9. Integration and wiring
  - [x] 9.1 Wire all components together in the app
    - Ensure `document-page.js` uses `markdown-renderer`, `loading-indicator`, and `error-display`
    - Ensure `app.js` wraps everything with `ErrorBoundary`
    - Verify the full flow: route → fetch → render markdown
    - _Requirements: 2.1, 3.1, 4.1, 5.1_

  - [ ]* 9.2 Write integration tests for end-to-end document viewing flow
    - Test navigating to a document path renders markdown content (mocked S3)
    - Test navigating to non-existent document shows not-found message
    - Test network error shows error with retry
    - _Requirements: 2.1, 2.4, 3.1, 3.4, 3.5, 5.4_

- [ ] 10. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Serverless Framework V4 is used for backend infrastructure
- All source files use JavaScript (no TypeScript) with kebab-case naming
- Checkpoints ensure incremental validation throughout implementation
