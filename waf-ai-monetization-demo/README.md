# WAF AI Traffic Monetization Demo

Minimal demo of [AWS WAF AI traffic monetization](https://docs.aws.amazon.com/waf/latest/developerguide/waf-ai-traffic-monetization.html)
for a publisher (AnyCompany Media). An AI bot requesting protected content from
a CloudFront distribution receives an HTTP `402 Payment Required` response with
a machine-readable x402 price manifest; browsers and search crawlers pass free.

> Built with **AWS CDK (Python)** to match this workspace's stack conventions.
> (The original spec referenced CDK TypeScript — see note at the bottom.)

## What gets deployed

- **S3 bucket** (private, OAC) serving 3 sample articles across content zones
- **CloudFront distribution** fronting the S3 origin
- **WAF Web ACL** (CLOUDFRONT scope, `us-east-1`) with:
  - AWS Managed Rules **Bot Control** (COMMON) classifying AI bots
  - **Monetize** rules returning 402 + x402 manifest for AI bots, priced per path
  - **Allow** as the default action (no charge for humans / search crawlers)

### Pricing model

The base price lives in `MonetizationConfig` (minimum `$0.001` USDC); each
Monetize rule scales it with a `PriceMultiplier` (1–100):

| Path           | Multiplier | Effective price |
|----------------|-----------:|----------------:|
| `/medical/*`   |        x10 |   `$0.010` USDC |
| `/automotive/*`|         x5 |   `$0.005` USDC |
| `/marketing/*` |         x3 |   `$0.003` USDC |

Runs in **TEST mode** on **Base Sepolia** — no real payments.

### Pricing model (billing) — pay-as-you-go

This stack uses **CloudFront pay-as-you-go** pricing. It does **not** attach a
CloudFront flat-rate plan (Free / Pro / Business / Premium) — those are a
separate resource and a console-only default; IaC-created distributions are
pay-as-you-go by construction. WAF and Bot Control are billed separately as
standard pay-as-you-go resources, and AI traffic monetization itself is included
at no additional charge (standard AWS WAF charges apply).

Approximate cost while deployed: **~$15–16/month** — WAF Web ACL (~$5/mo) +
Bot Control Common (~$10/mo + ~$1 per million requests) + negligible CloudFront
transfer for test traffic. Run `cdk destroy` promptly after the demo.

## Deploy

```bash
# Prerequisites: Node.js 18+, AWS CLI configured, CDK v2, Python 3.12+
cd infra
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: your Base Sepolia test wallet (defaults to a burn address otherwise)
export WALLET_ADDRESS="0xYourTestWalletAddress"

# Web ACL is CLOUDFRONT-scoped -> must deploy to us-east-1 (set in app.py)
cdk deploy --require-approval never
```

## Test

```bash
chmod +x scripts/test-demo.sh
./scripts/test-demo.sh <DistributionUrl-from-cdk-output>
```

The URL argument accepts a full `https://` URL or a bare hostname — the script
prepends `https://` automatically when no protocol is provided:

```bash
# Both forms work:
./scripts/test-demo.sh https://d1234abcdef.cloudfront.net
./scripts/test-demo.sh d1234abcdef.cloudfront.net
```

- Browser User-Agent → `200 OK` (free access)
- `GPTBot/1.0` / `Claude-Web/1.0` → `402 Payment Required` with the x402 price
  manifest returned as base64 JSON in the `payment-required` response header

The script decodes the manifest automatically when `jq` is installed, showing
the USDC price, network, and pay-to address for each content zone.

## Clean up

```bash
cd infra
cdk destroy --force
```

## Notes

- **Region:** AI-monetization Web ACLs are CLOUDFRONT-scoped and must live in
  `us-east-1`; `app.py` pins this.
- **Bot label:** the Monetize rules match the Bot Control AI-bot category label
  (`awswaf:managed:aws:bot-control:bot:category:ai`). If your account's Bot
  Control output uses a different label, update `AI_BOT_LABEL` in
  `infra/waf_monetization_stack.py`.
- **Going live:** flip `CurrencyMode` from `TEST` to `REAL` and switch the
  chain to `BASE` / `SOLANA` with a funded production wallet — no application
  code changes.
- **Language deviation:** the spec at
  `.kiro/specs/cloudfront-waf-monetisation/cf-waf-monetise.md` specified CDK
  TypeScript, but the workspace tech-stack rules mandate Python CDK and forbid
  TypeScript, so this was built in Python.
```
