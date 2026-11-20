# WAF AI Traffic Monetization Demo

## Overview

Build a minimal demo environment to showcase AWS WAF AI Traffic Monetization to a publisher (AnyCompany Media). The demo should demonstrate the full 402 payment-required flow when an AI bot requests content from a CloudFront distribution protected by WAF with a Monetize rule.

**Important:** CloudFront now offers flat-rate pricing plans (Free, Pro, Business, Premium) alongside the traditional **pay-as-you-go** model. For this demo, use **pay-as-you-go** pricing — no plan commitment required. WAF and Bot Control are added separately as standard pay-as-you-go resources. When creating the distribution, select "Pay-as-you-go" (or skip plan selection) to avoid a monthly plan commitment.

## Requirements

### Functional Requirements

1. **Static content origin** — An S3 bucket serving sample "publisher articles" (3-5 HTML pages simulating premium content from different content zones: `/automotive/`, `/medical/`, `/marketing/`)
2. **CloudFront distribution (pay-as-you-go)** — Create a distribution using standard pay-as-you-go pricing, serving the S3 origin with the default `*.cloudfront.net` domain. WAF and Bot Control are attached separately (not bundled via a flat-rate plan).
3. **WAF Web ACL with Bot Control** — Attached to the CloudFront distribution with AWS Managed Rules Bot Control (Common level)
4. **Monetization configuration** — A `MonetizationConfig` in TEST mode using Base Sepolia testnet, with differentiated pricing per content path:- `/automotive/*` → $0.005 USDC per request
- `/medical/*` → $0.01 USDC per request (premium content)
- `/marketing/*` → $0.003 USDC per request
5. **Monetize rules** — WAF rules that apply the `Monetize` action to requests labelled as AI bots by Bot Control
6. **Allow rules** — Requests from standard browsers and search engine crawlers are allowed (no charge)
7. **Sample test script** — A shell script (`test-demo.sh`) that:- Sends a request with a normal browser User-Agent → 200 OK
- Sends a request with `GPTBot/1.0` User-Agent → 402 Payment Required with x402 price manifest
- Sends a request with `Claude-Web/1.0` User-Agent → 402 Payment Required
- Pretty-prints the 402 response body (JSON price manifest)

### Non-Functional Requirements

- Infrastructure as Code using **AWS CDK (TypeScript)**
- Single-stack deployment (`cdk deploy` one-liner)
- **Cost (pay-as-you-go):** Minimal for a demo — WAF Web ACL ($5/mo), Bot Control Common ($10/mo + $1/M requests), CloudFront data transfer (negligible for test traffic). Total: ~$15–16/month while deployed. Destroy promptly after demo.
- Cleanup with `cdk destroy`
- All resources in `us-east-1` (required for CloudFront-scoped WAF)
- Total deployment time < 5 minutes
- No real payments — TEST mode only (Base Sepolia)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Internet                          │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│           Amazon CloudFront Distribution             │
│  ┌────────────────────────────────────────────────┐  │
│  │      AWS WAF Web ACL (Bot Control + Monetize)  │  │
│  │                                                │  │
│  │  Rule 1: If AI Bot label → Monetize action     │  │
│  │  Rule 2: If browser/search → Allow             │  │
│  │                                                │  │
│  │  MonetizationConfig:                           │  │
│  │    CurrencyMode: TEST                          │  │
│  │    Chain: BASE_SEPOLIA                         │  │
│  │    Prices: path-based (0.003–0.01 USDC)        │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              Amazon S3 (Origin)                       │
│                                                      │
│  /automotive/index.html  — sample Autocar article    │
│  /medical/index.html     — sample MIMS article       │
│  /marketing/index.html   — sample Campaign article   │
└──────────────────────────────────────────────────────┘

```

## Project Structure

```
waf-ai-monetization-demo/
├── README.md                  ← Quick-start instructions
├── bin/
│   └── app.ts                 ← CDK app entry point
├── lib/
│   └── waf-monetization-stack.ts  ← Main CDK stack
├── content/
│   ├── automotive/
│   │   └── index.html         ← Sample automotive article
│   ├── medical/
│   │   └── index.html         ← Sample medical article
│   └── marketing/
│       └── index.html         ← Sample marketing article
├── scripts/
│   └── test-demo.sh           ← curl-based test script
├── cdk.json
├── tsconfig.json
├── package.json
└── .gitignore

```

## Implementation Details

### CDK Stack (`lib/waf-monetization-stack.ts`)

1. **S3 Bucket** — Private bucket with OAC (Origin Access Control) for CloudFront
2. **CloudFront Distribution (pay-as-you-go)** — Default cache behavior pointing to S3, OAC configured. Standard pay-as-you-go pricing (no flat-rate plan selection needed in CDK).
3. **WAF Web ACL** (scope: CLOUDFRONT, region: us-east-1):
   - Add Bot Control managed rule group subscription (Common level, billed separately at $10/mo + $1/M requests)
- Custom rule: Match on WAF label `awswaf:managed:aws:bot-control:bot:category:ai` → Action: `Monetize`
- Custom rule: Match all other traffic → Action: `Allow`
- `MonetizationConfig`:```json
{
  "CurrencyMode": "TEST",
  "CryptoConfig": {
    "PaymentNetworks": [{
      "Chain": "BASE_SEPOLIA",
      "WalletAddress": "<PLACEHOLDER_WALLET>",
      "Prices": [{ "Amount": "0.005", "Currency": "USDC" }]
    }]
  }
}

```
4. **S3 Deployment** — Use `BucketDeployment` to upload the `content/` folder to S3

### Sample Content Pages

Each HTML page should be a simple, realistic-looking article:

- AnyCompany branding colours (dark navy + red accent)
- Title, author, date, 2-3 paragraphs of lorem ipsum styled as a news article
- Footer: "© 2026 AnyCompany Media Group — Premium Content"

### Test Script (`scripts/test-demo.sh`)

```bash
#!/bin/bash
DISTRIBUTION_URL="$1"  # Pass CloudFront URL as argument

echo "=== Test 1: Normal browser request (should return 200) ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  "$DISTRIBUTION_URL/automotive/index.html"

echo ""
echo "=== Test 2: GPTBot request (should return 402) ==="
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "User-Agent: GPTBot/1.0 (+https://openai.com/gptbot)" \
  "$DISTRIBUTION_URL/automotive/index.html" | jq .

echo ""
echo "=== Test 3: Claude-Web request (should return 402) ==="
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "User-Agent: Claude-Web/1.0 (+https://anthropic.com/claude-web)" \
  "$DISTRIBUTION_URL/medical/index.html" | jq .

```

## Deployment Instructions (README.md)

```bash
# Prerequisites: Node.js 18+, AWS CLI configured, CDK v2 installed
# ⚠️  Cost: ~$15/month (WAF $5 + Bot Control $10) while deployed. Destroy after demo.

# 1. Install dependencies
npm install

# 2. Set your test wallet address (Base Sepolia)
export WALLET_ADDRESS="0xYourTestWalletAddress"

# 3. Deploy
cdk deploy --require-approval never

# 4. Test (URL printed in CDK outputs)
chmod +x scripts/test-demo.sh
./scripts/test-demo.sh https://d1234abcdef.cloudfront.net

# 5. Cleanup
cdk destroy --force

```

## Success Criteria

- [ ] `cdk deploy` completes without errors
- [ ] Browser request to any path returns 200 with HTML content
- [ ] Request with AI bot User-Agent returns 402 with JSON body containing `price`, `payTo`, `network` fields
- [ ] Different content paths show correct differentiated pricing in the 402 response
- [ ] `cdk destroy` cleanly removes all resources

## Notes for the Demo

- The 402 response body is the "money shot" — it shows the machine-readable price manifest that AI agents receive
- Emphasise: zero application code changes, entirely edge-side configuration
- Point out the Bot Control label matching — over 650 AI bot types are classified automatically
- Mention that switching from TEST to REAL mode is a single toggle (CurrencyMode)
- Revenue dashboard populates in real-time once live traffic flows

