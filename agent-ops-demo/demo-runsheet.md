# AgentOps demo — runsheet (14:15–15:00)

Operate & trust an agent: **invoke → open trace → show denial → show eval**.
The agent is just something to observe; the AgentOps layer is the story.

**Before you start (once):**
Refresh Midway (force, so a stale session can't cause a mid-demo `used_too_late` failure):
```bash
mwinit -f
```
Point the shell at the demo project and account (host commands use the `default` profile, which calls `ada` for you — no credential juggling):
```bash
cd agent-ops-demo/agentops
```
```bash
export AWS_PROFILE=default
```
```bash
export AWS_REGION=eu-west-1
```
Confirm the runtime is up:
```bash
agentcore status
```
Expect: `agentops  Deployed - Runtime: READY`. If anything is down, present from `demo-fallback/` — every step has a static artifact there.

---

## 1 · Invoke (R1) — ~1 min
"Here's the workshop's starter agent, unchanged. One call."
```bash
agentcore invoke "What is the weather in Athens?"
```
Expect: *"The weather in Athens is very sunny! ☀️"*. It also prints a `Session: <id>` line.

## 1b · Capture the Session ID — ~15 sec
So step 4 needs no copy-paste, capture the session into a shell variable. This invokes once and stores the id in `$SID`:
```bash
SID=$(agentcore invoke --json "What is the weather in Athens?" | python3 -c 'import sys,json; print(json.load(sys.stdin)["sessionId"])')
```
Confirm it captured:
```bash
echo "$SID"
```
→ prints a UUID like `33b05303-6021-4772-8eb5-b6d85bc36a21`. You'll reuse `$SID` in step 4.
*(Keep this terminal open — `$SID` only lives in this shell session.)*

## 2 · Open the trace (R2) — ~3 min
"Every call emits an OpenTelemetry trace — session → trace → span."
- CloudWatch → **GenAI Observability** (eu-west-1), pick the latest `agentops` session, **or**:
```bash
agentcore traces
```
Point out, on one span: the **model call** (`chat`, tokens + TTFT), the **tool call**
(`execute_tool weather`), and the **decision** (`gen_ai.choice`).
*(Cost/latency glance, R5: ~4.5s end-to-end, 2 model calls, 1 tool call, ~4100 tokens — ties back to model routing.)*
Fallback: `demo-fallback/R2-trace.md` + `R2-trace-span.json`.

## 3 · Show the denial (R3) — THE MONEY MOMENT — ~4 min
"A Cedar policy gates a privileged tool at the gateway — deterministically, outside the agent's reasoning. Default-deny."
**ALLOWED** — small refund ($500, under the $1000 limit). One line, paste and run:
```bash
curl -s -X POST "https://agentops-policygateway-sf1co0tlqb.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"RefundTarget___process_refund","arguments":{"amount":500}}}'
```
→ `{"result":{"isError":false, ... "status":"refunded","amount":500 ...}}`

**DENIED** — large refund ($5000). Same tool, same gateway:
```bash
curl -s -X POST "https://agentops-policygateway-sf1co0tlqb.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"RefundTarget___process_refund","arguments":{"amount":5000}}}'
```
→ **`Tool Execution Denied ... [No policy applies to the request (denied by default).]`** — the Lambda never ran; nothing mutated.

Fallback: `demo-fallback/R3-policy-denial.md`.

## 4 · Show the eval (R4) — ~4 min
"Two graders on that one interaction: a deterministic check and an LLM judge."
```bash
agentcore run eval --runtime agentops --evaluator ToolAndPolicyCheck HelpfulnessJudge --session-id "$SID"
```
*(If `$SID` isn't set — e.g. you opened a fresh terminal — paste the UUID from the step-1 `Session:` line in place of `"$SID"`.)*
- **ToolAndPolicyCheck** → `Pass` (expected `weather` tool was called; 0 tokens — pure code, reproducible).
- **HelpfulnessJudge** → `5 / Excellent` with a one-paragraph explanation.
Fallback: `demo-fallback/R4-eval-result.md` + `R4-eval-result.json`.

---

## Close (~30s)
Observability (read what it did) + Governance (a deterministic deny it can't argue past)
+ Evaluation (deterministic + judge) = the three things you need to **operate and trust** an agent.

## Timing
| Step | Target |
|---|---|
| Invoke | 1 min |
| Trace | 3 min |
| **Denial** | **4 min (protect this)** |
| Eval | 4 min |
| Close + buffer | ~2 min |

## If short on time (cut-list)
Keep **1 (invoke) + 2 (trace) + 3 (denial)** — a strong 10-min operator walk-through.
Show 4 (eval) and the R5 cost glance as static screens from `demo-fallback/`.
