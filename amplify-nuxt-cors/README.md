# Amplify + Nuxt 3 SSG Reproduction App

Minimal Nuxt 3 Static Site Generation app that reproduces the exact issues experienced on AWS Amplify Hosting: direct URL 404s, SPA rewrite conflicts, CORS errors from Sanity.io CMS, trailing slash failures, and all-routes-redirect-to-home behavior.

These issues are traced to Amplify's default SPA catch-all rewrite rule being incompatible with Nuxt SSG output. See [aws-amplify/amplify-hosting#3829](https://github.com/aws-amplify/amplify-hosting/issues/3829) for the upstream bug report.

## Background

When Nuxt 3 generates a static site (`nuxt generate`), it produces per-route `index.html` files (e.g., `valuation/index.html`, `blog/post-1/index.html`). Amplify's default SPA catch-all rewrite rule intercepts clean URLs and serves the root `/index.html` instead, breaking direct URL access for every route.

The SPA catch-all rule:

```
</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>  →  /index.html  (200)
```

This rule matches any URL without a file extension (or with an unrecognized extension) and rewrites it to `/index.html` with a 200 status — designed for SPAs but destructive for SSG apps.

## Prerequisites

- **Node.js 22** or later
- **AWS account** with Amplify Hosting access
- **Git** repository connected to Amplify (GitHub, GitLab, Bitbucket, or CodeCommit)
- (Optional) Sanity.io project for CMS proxy testing

## Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd amplify-nuxt-cors

# Install dependencies
npm install

# Start local dev server
npm run dev
```

Visit [http://localhost:3000/diagnostics](http://localhost:3000/diagnostics) to see the diagnostic dashboard.

Locally, route checks will pass (no Amplify rewrite interference). The CORS test will demonstrate the browser CORS block for direct Sanity API calls vs. successful proxy calls.

## Deploy to Amplify

1. Push this repository to a Git provider (GitHub, etc.)
2. Open the [AWS Amplify Console](https://eu-west-1.console.aws.amazon.com/amplify/home?region=eu-west-1) in **eu-west-1**
3. Click **New app** → **Host web app**
4. Connect your repository and select the branch
5. Amplify will auto-detect `amplify.yml` — confirm the build settings:
   - Build command: `npm run generate`
   - Artifact base directory: `.output/public`
6. Deploy and wait for the build to complete
7. Visit `<your-amplify-url>/diagnostics` to verify the broken behavior

The default `amplify.yml` includes the SPA catch-all rewrite rule, which reproduces all the issues listed below.


## Issue Reproduction Table

Once deployed with the default `amplify.yml` (broken mode), the diagnostic dashboard at `/diagnostics` confirms each issue:

| Issue | Diagnostic Test | Category | Expected Result (Broken Mode) |
|---|---|---|---|
| Direct URL returns 404 or wrong page | `Direct access: /valuation` (and all non-home routes) | `route` | ❌ HTTP 200 but serves home page content, or 404 |
| Nested route 404 | `Direct access: /blog/post-1` | `route` | ❌ HTTP 200 but serves home page content, or 404 |
| Trailing slash failure | `Trailing slash: /valuation/` (and all routes) | `trailing-slash` | ❌ HTTP 404 or serves home page |
| All routes redirect to home | `Content verify: /about` (and all non-home routes) | `content` | ❌ "Served home page content instead of correct page" |
| CORS error on Sanity API | `CORS: Direct Sanity API call` | `cors` | ✅ CORS error detected (confirms browser blocks direct call) |
| `/index.html` suffix works | Manual: visit `/valuation/index.html` | — | ✅ HTTP 200 with correct content |
| Client-side navigation works | Manual: click NuxtLink from home to `/valuation` | — | ✅ Correct page renders (client routing unaffected) |

The root cause for all route-related failures is the SPA catch-all rewrite rule in `amplify.yml`. It rewrites clean URLs to `/index.html`, so the browser receives home page content at every URL.

## Fix Mode

To verify the fix, swap the Amplify build spec to remove the SPA catch-all rule:

1. Copy the fix build spec over the default:
   ```bash
   cp amplify-fix.yml amplify.yml
   ```
2. Commit and push the change:
   ```bash
   git add amplify.yml
   git commit -m "Switch to fix mode (remove SPA catch-all)"
   git push
   ```
3. Amplify will automatically rebuild and redeploy
4. Visit `<your-amplify-url>/diagnostics` to verify all route and content checks now pass

The `amplify-fix.yml` removes the SPA catch-all rewrite entirely. Amplify then serves the pre-rendered `index.html` files from each route's directory naturally (e.g., `/valuation` → `valuation/index.html`).

To switch back to broken mode for comparison, restore the original `amplify.yml` from git:

```bash
git checkout HEAD~1 -- amplify.yml
git commit -m "Revert to broken mode"
git push
```

You can identify which mode is active by checking the `X-Repro-Mode` response header: `broken` or `fixed`.

## Failed Fix Attempts

The following approaches were tried before identifying the SPA catch-all rule as the root cause. Each failed to fully resolve the issues:

### 1. CORS Header Updates

Added custom CORS headers (`Access-Control-Allow-Origin`, etc.) in `amplify.yml` custom headers section.

**Why it failed:** CORS headers on the Amplify response don't help because the issue is the Sanity.io API server not including the correct CORS headers for the requesting origin. The Amplify-hosted app's own headers are irrelevant to cross-origin requests made from the browser to a third-party API. The real fix is server-side proxying via Nuxt server routes.

### 2. Amplify Reverse Proxy

Attempted to use Amplify rewrite rules to proxy requests to the Sanity API (rewrite `/api/sanity` → `https://your-project-id.apicdn.sanity.io`).

**Why it failed:** Amplify's rewrite rules for reverse proxying have limitations with query parameters, authentication headers, and response transformation. The proxy didn't reliably forward GROQ queries or handle Sanity's response format. Nuxt server routes (`server/api/`) are a more reliable and flexible proxy mechanism.

### 3. Removing SPA Rewrite Only (Without Full Testing)

Removed the SPA catch-all rule but kept other redirect/rewrite rules that conflicted with Nuxt's output structure.

**Why it failed:** Partial removal fixed direct URL access but introduced trailing slash inconsistencies. The clean fix requires removing the SPA catch-all entirely and relying on Amplify's default static file serving, which correctly maps `/valuation` to `valuation/index.html`.

### 4. Nuxt Config Changes

Tried various `nuxt.config.js` adjustments: setting `router.trailingSlash`, changing `nitro.preset`, adjusting `generate` options, and modifying `routeRules`.

**Why it failed:** The issue is not in Nuxt's build output — `nuxt generate` correctly produces per-route `index.html` files. The problem is Amplify's rewrite engine intercepting requests before they reach the static files. No Nuxt configuration change can override Amplify's server-side rewrite rules.

### 5. Redirect/Rewrite Pattern Matching

Attempted to add Amplify redirect rules that match specific routes and serve the correct files (e.g., `/valuation` → `/valuation/index.html` 200).

**Why it failed:** This approach requires maintaining a redirect rule for every route, which doesn't scale. It also conflicts with the SPA catch-all rule's regex — the catch-all has broad precedence and matches before specific route rules. Amplify processes rules in order, and the catch-all's regex pattern is too greedy to coexist with route-specific rules.

## Architecture Notes

```
amplify-nuxt-cors/
├── nuxt.config.js              # ssr: true, nitro preset: static
├── package.json                # dev, generate, preview scripts
├── amplify.yml                 # Broken mode (SPA catch-all active)
├── amplify-fix.yml             # Fix mode (no SPA catch-all)
├── app.vue                     # Root shell with NavBar + NuxtPage
├── pages/                      # Route pages (each gets pre-rendered HTML)
│   ├── index.vue               # /
│   ├── valuation.vue           # /valuation
│   ├── login.vue               # /login
│   ├── about.vue               # /about
│   ├── contact.vue             # /contact
│   ├── diagnostics.vue         # /diagnostics (dashboard)
│   └── blog/
│       ├── index.vue           # /blog
│       ├── post-1.vue          # /blog/post-1
│       └── post-2.vue          # /blog/post-2
├── components/
│   ├── NavBar.vue              # Navigation (NuxtLink to all routes)
│   ├── DiagnosticRunner.vue    # Runs automated diagnostic checks
│   ├── TestResultCard.vue      # Single test result display
│   └── SanityDemo.vue          # Direct vs. proxy Sanity API demo
├── composables/
│   ├── useDiagnostics.js       # Diagnostic check logic and summary
│   ├── useSanity.js            # Sanity API client (direct + proxy)
│   └── useRouteTests.js        # Route definitions with expected titles
├── server/api/
│   └── sanity.js               # Server-side Sanity proxy (no CORS)
└── .env.example                # Environment variable template
```

The diagnostic dashboard (`/diagnostics`) runs four categories of automated checks:
- **Route checks** — Direct URL access to each route via `fetch()`
- **Trailing slash checks** — Same routes with trailing slash appended
- **CORS check** — Client-side fetch to Sanity API (expects CORS block)
- **Content verification** — Compares response HTML title against expected page title to detect the redirect-to-home bug

The Sanity.io CMS proxy pattern uses Nuxt server routes (`server/api/sanity.js`) to make API calls server-side, avoiding browser CORS restrictions entirely.
