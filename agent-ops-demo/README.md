# AgentOps demo — operate & trust an agent

The **operations layer** built on top of the workshop's starter agent:
**observability** (traces), **governance** (an observable policy denial), and
**evaluation** (deterministic + LLM-as-judge). We reuse the starter agent as-is;
we do not build a new agent.

Region **eu-west-1**, account **123456789012**. Synthetic data only.

## Layout
```
agent-ops-demo/
├── agentops/            # the deployed AgentCore project (agentcore CLI)
│   ├── app/agentops/            main.py — starter agent (weather + calculator)
│   ├── app/ToolAndPolicyCheck/  deterministic code-based evaluator (R4)
│   └── agentcore/               project config (runtime, gateway, policy, evaluators)
├── policy/              # R3 assets: refund tool schema, Cedar policies, Lambda + script
├── agent/              # the extracted starter agent (source of truth, provenance)
├── demo-fallback/       # static evidence for every requirement (R2–R5)
├── demo-runsheet.md     # on-stage order + exact commands
└── README.md            # this file
```

## Deployed resources (target `default`, eu-west-1)
| Resource | Name / ARN |
|---|---|
| Runtime | `agentops_agentops-133RNOGqJm` |
| Policy gateway | `agentops-policygateway-sf1co0tlqb` (MCP, auth NONE) |
| Gateway target | `RefundTarget` → Lambda `agentops-process-refund` (synthetic) |
| Policy engine | `agentops_RefundPolicyEngine-0uqdoipa26` (ENFORCE) |
| Cedar policy | `RefundLimit` — permit `process_refund` when `amount < 1000` |
| Deterministic eval | `agentops_ToolAndPolicyCheck-*` |
| LLM-as-judge eval | `agentops_HelpfulnessJudge-*` (Sonnet 4.5, 1–5 scale) |

## Requirements → evidence
| Req | What | Verified | Fallback |
|---|---|---|---|
| R1 | starter agent invokes cleanly | ✅ `agentcore invoke` → 200 | — |
| R2 | readable trace (session→trace→span) | ✅ real OTEL spans in CloudWatch | `demo-fallback/R2-trace.md` |
| R3 | observable default-deny policy | ✅ $5000 → deterministic DENY | `demo-fallback/R3-policy-denial.md` |
| R4 | deterministic + judge eval | ✅ Pass + 5/5 with explanation | `demo-fallback/R4-eval-result.*` |
| R5 | cost/latency glance | ✅ tokens/latency/iterations | `demo-fallback/R2-trace.md` |
| R6 | fallback pack | ✅ | `demo-fallback/` |

## Quick start
Host commands (`status`, `invoke`, `run eval`, `deploy`) use the `default`
profile, whose `credential_process` calls `ada` on the host — no credential
materialization needed. (That was only required for the local `agentcore dev`
*container*, which can't see `ada`.)
```bash
cd agentops
```
```bash
export AWS_PROFILE=default
```
```bash
export AWS_REGION=eu-west-1
```
```bash
agentcore status
```
```bash
agentcore invoke "What is the weather in Athens?"
```
```bash
agentcore run eval --runtime agentops --evaluator ToolAndPolicyCheck HelpfulnessJudge --session-id <SESSION_ID>
```
Full on-stage flow: **`demo-runsheet.md`**.

## How it was built (key decisions)
- **Container build, not code-zip.** OTEL traces only export when the runtime
  launches under `opentelemetry-instrument`; the `agentcore` CLI's Container
  build does this, the hand-rolled code-zip `create_agent_runtime` path does not.
- **Policy enforces on gateway tools.** Cedar gates tools routed through an
  AgentCore Gateway, so the privileged action (`process_refund`) is a gateway
  Lambda target — not one of the agent's in-process tools.
- **Two evaluator kinds.** A code-based Lambda (deterministic, 0 tokens) plus an
  LLM-as-judge (rubric score + explanation).

## Rebuild from scratch
Agent + deploy: see `agentops/` and `agent/README.md`.
Policy (R3): `policy/create_refund_lambda.sh`, then the `agentcore add gateway /
gateway-target / policy-engine / policy` sequence in `demo-runsheet.md` step 3.

## Teardown
The project's runtime, gateway, policy engine, and evaluators are all in one CDK
stack — delete it, then remove the standalone synthetic Lambda.
```bash
# 1) delete the CDK stack (runtime + gateway + policy engine + evaluators)
aws cloudformation delete-stack --stack-name AgentCore-agentops-default --region eu-west-1
aws cloudformation wait stack-delete-complete --stack-name AgentCore-agentops-default --region eu-west-1

# 2) delete the standalone synthetic refund Lambda + its role
aws lambda delete-function --function-name agentops-process-refund --region eu-west-1
aws iam detach-role-policy --role-name agentops-refund-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name agentops-refund-lambda-role
```
(`agentcore remove <resource>` + `agentcore deploy` also works to remove
individual resources from the stack without tearing it all down.)
