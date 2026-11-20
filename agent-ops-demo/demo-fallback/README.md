# Demo fallback pack

Everything needed to present the AgentOps demo from **static artifacts** if the
live environment misbehaves. Each requirement has a readable writeup plus the
raw data it was drawn from.

| File | Requirement | What it shows |
|---|---|---|
| `R2-trace.md` | R2 — readable trace | session → trace → span breakdown (model call, tool call, decision) |
| `R2-trace-span.json` | R2 (raw) | a real `chat` span with inline gen_ai.* events |
| `R2-trace.md` (R5 section) | R5 — cost/latency glance | tokens, latency, TTFT, iteration/tool-call counts for one run |
| `R3-policy-denial.md` | R3 — policy denial | the allow (\$500) vs deterministic DENY (\$5000) at the gateway |
| `R4-eval-result.md` | R4 — evals | deterministic Pass + LLM-judge score 5/5 with explanation |
| `R4-eval-result.json` | R4 (raw) | the exact `agentcore run eval` output |

## Live environment (if it's up)
- Runtime: `agentops_agentops-133RNOGqJm` (eu-west-1, account 123456789012)
- Gateway (policy): `agentops-policygateway-sf1co0tlqb`
- Evaluators: `agentops_ToolAndPolicyCheck-*` (deterministic), `agentops_HelpfulnessJudge-*` (judge)

See `../demo-runsheet.md` for the on-stage order and exact commands.
