# R3 — Observable policy denial (captured evidence)

**The money moment.** A privileged tool (`process_refund`) is gated by a Cedar
policy at the AgentCore Gateway, enforced deterministically outside the agent's
reasoning loop. Default-deny: anything not explicitly permitted is blocked.

## Setup (deployed)
- Gateway: `agentops-policygateway-sf1co0tlqb`
  URL: `https://agentops-policygateway-sf1co0tlqb.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp`
- Target: `RefundTarget` → Lambda `agentops-process-refund` (synthetic; no money moves)
- Policy engine: `agentops_RefundPolicyEngine-0uqdoipa26` — attached ENFORCE
- Policy `RefundLimit` (Cedar, enforcementMode ACTIVE):

```cedar
permit (principal,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:eu-west-1:123456789012:gateway/agentops-policygateway-sf1co0tlqb")
when { context.input.amount < 1000 };
```

## Demonstration (same gateway, two amounts)

**Allowed — amount = 500 (matches `permit`, < 1000):**
```json
{"jsonrpc":"2.0","id":1,"result":{"isError":false,"content":[{"type":"text",
  "text":"{\"status\":\"refunded\",\"amount\":500,\"note\":\"SYNTHETIC demo refund — no money moved.\"}"}]}}
```

**Denied — amount = 5000 (no permit matches → default-deny):**
```json
{"jsonrpc":"2.0","id":1,"error":{"code":-32002,
  "message":"Tool Execution Denied: Tool call not allowed due to policy enforcement [No policy applies to the request (denied by default).]"}}
```

## Why this is the strong moment
- **Deterministic**: the decision is the policy engine's, not the model's — same
  input always yields the same allow/deny.
- **Outside the agent**: enforced at the gateway boundary; the agent cannot talk
  its way past it.
- **Nothing mutated**: on denial the Lambda never executes.
- **Default-deny**: the error text literally says "denied by default" — the
  posture the spec asks to demonstrate.

## Reproduce live
```bash
GW="https://agentops-policygateway-sf1co0tlqb.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp"
# denied
curl -s -X POST "$GW" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"RefundTarget___process_refund","arguments":{"amount":5000}}}'
# allowed
# ...same with "amount":500
```

_Note: AgentCore also logs policy decisions to CloudWatch; indexing can lag a few
minutes after first traffic. The enforced gateway response above is the primary
evidence._
