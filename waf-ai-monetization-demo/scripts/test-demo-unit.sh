#!/bin/bash
# Unit tests for test-demo.sh URL normalization logic.
# Validates that the protocol-prefix and trailing-slash handling works correctly.
#
# Usage: ./scripts/test-demo-unit.sh
set -euo pipefail

PASS=0
FAIL=0

assert_eq() {
  local description="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $description"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $description"
    echo "        expected: $expected"
    echo "        actual:   $actual"
    FAIL=$((FAIL + 1))
  fi
}

# Simulate the normalization logic from test-demo.sh
normalize_url() {
  local DISTRIBUTION_URL="$1"
  # Ensure https:// prefix if no protocol was provided.
  if [[ "$DISTRIBUTION_URL" != http://* && "$DISTRIBUTION_URL" != https://* ]]; then
    DISTRIBUTION_URL="https://$DISTRIBUTION_URL"
  fi
  # Strip trailing slash
  DISTRIBUTION_URL="${DISTRIBUTION_URL%/}"
  echo "$DISTRIBUTION_URL"
}

echo "=== URL normalization tests ==="

# Test: bare hostname gets https:// prepended
assert_eq "bare hostname gets https:// prefix" \
  "https://d1234abcdef.cloudfront.net" \
  "$(normalize_url "d1234abcdef.cloudfront.net")"

# Test: bare hostname with trailing slash
assert_eq "bare hostname with trailing slash is normalized" \
  "https://d1234abcdef.cloudfront.net" \
  "$(normalize_url "d1234abcdef.cloudfront.net/")"

# Test: https:// URL is preserved as-is
assert_eq "https:// URL is unchanged" \
  "https://d1234abcdef.cloudfront.net" \
  "$(normalize_url "https://d1234abcdef.cloudfront.net")"

# Test: https:// URL with trailing slash
assert_eq "https:// URL trailing slash stripped" \
  "https://d1234abcdef.cloudfront.net" \
  "$(normalize_url "https://d1234abcdef.cloudfront.net/")"

# Test: http:// URL is preserved (not upgraded)
assert_eq "http:// URL is preserved" \
  "http://localhost:8080" \
  "$(normalize_url "http://localhost:8080")"

# Test: http:// URL with trailing slash
assert_eq "http:// URL trailing slash stripped" \
  "http://localhost:8080" \
  "$(normalize_url "http://localhost:8080/")"

# Test: bare hostname with port
assert_eq "bare hostname with port gets https:// prefix" \
  "https://localhost:4566" \
  "$(normalize_url "localhost:4566")"

# Test: subdomain.domain.tld pattern
assert_eq "subdomain pattern gets https:// prefix" \
  "https://waf-demo.example.com" \
  "$(normalize_url "waf-demo.example.com")"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
