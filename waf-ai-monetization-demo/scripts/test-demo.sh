#!/bin/bash
# Validates the WAF AI monetization flow against a deployed CloudFront URL.
#
# Usage: ./test-demo.sh https://d1234abcdef.cloudfront.net
#
# Expected:
#   Browser User-Agent    -> 200 OK (free)
#   AI bot User-Agent     -> 402 Payment Required + x402 price manifest
#                            (manifest is returned in the `payment-required`
#                             response HEADER as base64 JSON, not the body)
set -euo pipefail

DISTRIBUTION_URL="${1:-}"
if [[ -z "$DISTRIBUTION_URL" ]]; then
  echo "Usage: $0 <cloudfront-url>" >&2
  exit 1
fi
# Ensure https:// prefix if no protocol was provided.
if [[ "$DISTRIBUTION_URL" != http://* && "$DISTRIBUTION_URL" != https://* ]]; then
  DISTRIBUTION_URL="https://$DISTRIBUTION_URL"
fi
DISTRIBUTION_URL="${DISTRIBUTION_URL%/}"

have_jq() { command -v jq >/dev/null 2>&1; }

# Print status + decoded x402 manifest (price in USDC) for an AI bot request.
show_402() {
  local label="$1" ua="$2" path="$3"
  echo "=== $label ==="
  local headers code manifest_b64
  headers=$(curl -s -D - -o /dev/null -w "HTTP Status: %{http_code}\n" \
              -H "User-Agent: $ua" "$DISTRIBUTION_URL$path")
  echo "$headers" | grep -i "^HTTP Status:"
  manifest_b64=$(echo "$headers" | tr -d '\r' \
                  | awk -F': ' 'tolower($1)=="payment-required"{print $2}')
  if [[ -z "$manifest_b64" ]]; then
    echo "  (no payment-required header — request was not monetized)"
  elif have_jq; then
    echo "$manifest_b64" | base64 -d | jq '{
      price_usdc: (((.accepts[0].amount | tonumber) / 1000000) | tostring),
      currency:   .accepts[0].extra.name,
      network:    .accepts[0].network,
      payTo:      .accepts[0].payTo,
      resource:   .resource.url,
      x402Version
    }'
  else
    echo "  payment-required (base64): $manifest_b64"
    echo "  (install jq to pretty-print the decoded manifest)"
  fi
  echo ""
}

echo "Target: $DISTRIBUTION_URL"
echo ""

echo "=== Test 1: Normal browser request to /automotive (expect 200) ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  "$DISTRIBUTION_URL/automotive/index.html"
echo ""

show_402 "Test 2: GPTBot -> /automotive (expect 402, \$0.005)" \
  "GPTBot/1.0 (+https://openai.com/gptbot)" "/automotive/index.html"

show_402 "Test 3: GPTBot -> /medical (expect 402, \$0.010)" \
  "GPTBot/1.0 (+https://openai.com/gptbot)" "/medical/index.html"

show_402 "Test 4: GPTBot -> /marketing (expect 402, \$0.003)" \
  "GPTBot/1.0 (+https://openai.com/gptbot)" "/marketing/index.html"
