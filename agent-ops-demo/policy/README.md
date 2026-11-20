# R3 — Observable policy denial (Cedar default-deny)

The **money moment**: a privileged action is denied by a Cedar policy at the
AgentCore Gateway, deterministically, outside the agent's reasoning loop — and
the DENY is visible in the trace / CloudWatch.

## Why a gateway tool (not the in-process tools)
AgentCore Policy engines enforce on **gateway tools** — every tool call routed
through an AgentCore Gateway is evaluated against Cedar policies before it runs.
The starter agent's own tools (`weather`, `calculator`) are **in-process Strands
tools**, so a policy engine can't intercept them. To show a real, enforced DENY
we add one privileged action as a **gateway tool** (`process_refund` backed by a
Lambda target) and govern it with Cedar.

## Semantics (from AgentCore docs)
- **Default-deny:** a call is denied unless a `permit` matches.
- **forbid-wins:** any matching `forbid` overrides every `permit`.
- **Logged:** policy decisions are written to CloudWatch — that's what makes the
  denial observable in the demo.

## Files
- `refund_tools.json` — tool schema for the gateway target (`process_refund`).
- `refund_policy.cedar` — allow refunds **< $1000** only. A $5000 refund matches
  no permit → **denied by default**.
- `refund_policy_forbid.cedar` — alternative: permit generally but **forbid ≥ $1000**
  (explicit deny, reads cleanest on a projector).

Both pin `resource == AgentCore::Gateway::"<GATEWAY_ARN>"` and the action id
`AgentCore::Action::"RefundTarget___process_refund"` (`<TargetName>___<toolName>`).

## Build order (two deploys — the policy needs the gateway ARN)
```bash
export AWS_PROFILE=default AWS_REGION=eu-west-1

# 1) Gateway + Lambda target + policy engine (ENFORCE)
agentcore add gateway --name PolicyGateway --authorizer-type NONE --runtimes <AGENT_RUNTIME>
agentcore add gateway-target --name RefundTarget --type lambda-function-arn \
  --lambda-arn <REFUND_LAMBDA_ARN> --tool-schema-file refund_tools.json --gateway PolicyGateway
agentcore add policy-engine --name RefundPolicyEngine \
  --attach-to-gateways PolicyGateway --attach-mode ENFORCE
agentcore deploy

# 2) read the gateway ARN, substitute into the .cedar file, then:
agentcore status
agentcore add policy --name RefundLimit --engine RefundPolicyEngine --source refund_policy.cedar
agentcore deploy
```

Simplest path for the ARN substitution: `agentcore add policy --generate "Only allow
refunds under 1000 dollars" --gateway PolicyGateway` (resolves the ARN for you).

## Trigger the denial (demo)
Ask the agent to process a **$5000** refund. The gateway evaluates the Cedar
policy, finds no permit (or a matching forbid), and returns a deterministic
**DENY** — nothing is mutated. Capture the decision from the trace / CloudWatch
for the fallback pack (R6).

## Note on the existing repo gateway
This repo already has `da-analytics-gateway-sy5tyy0uzp` (see
`agent-core-mcp-demo/deploy/outputs/gateway.json`). It can host the policy engine
instead of creating `PolicyGateway`, if you'd rather reuse it.
