# Kiro Build Spec — AgentOps Demo
### Cambridge Consultants workshop · AgentOps slot 14:15–15:00 · demo build

**Scope:** This is an **AgentOps** demo — operating and trusting an agent, not building one. Start from the workshop's **existing starter agent** and build only the operations layer on top. The Engineering Delivery Copilot is a *different* session (13:30) — do NOT build it here.

**Purpose:** produce the AgentOps artifacts you'll show live (or screen-capture): a **trace** to read, an **eval** to run (deterministic + LLM-as-judge), and an **observable policy denial**. The agent itself is just something to observe.

**How to use in Kiro:** one-off demo → **steering + requirements only, no SKILL.md**. Drop the steering file into `.kiro/steering/`, then paste the requirements as the build prompt. Pin **Sonnet 4.6** or **Auto** for speed/consistency (not Opus).

---

## 0. Prerequisites

- AWS account, **eu-west-1 (Ireland)**; confirm AgentCore + model are available there.
- AWS CLI + credentials; Python 3.11+; AgentCore CLI installed.
- The official AgentCore workshop starter (*Diving Deep into Bedrock AgentCore*, refreshed 6 Aug) — its **starter agent is the base you observe**. Do not build a new agent.
- Model access (eu-west-1): use an EU/global inference profile — `eu.anthropic.claude-sonnet-5` or `global.anthropic.claude-sonnet-5` (bare model ID isn't supported for on-demand).
- Non-prod account, spend limit, least-privilege role. **Synthetic data only.**

---

## 1. `.kiro/steering/agentops-demo.md` (inclusion: always)

```markdown
---
inclusion: always
---
# Project: AgentOps demo (operate & trust an agent)

## What this is
A DEMO of the AgentOps layer for a technical workshop. We take the workshop's
EXISTING starter agent as given and build only the operations artifacts on top:
observability (traces), evaluation (deterministic + LLM-as-judge), and governance
(an observable policy denial). We are NOT building a delivery agent or any new
agent logic — that's a separate session.

## Non-negotiables
- Do NOT author a new agent or business flow. Reuse the starter agent as-is.
- Synthetic data only. Keep everything projector-legible.
- The three deliverables are: (1) a readable trace, (2) an eval result with a
  judge explanation, (3) a visible default-deny policy decision.
- Pin Sonnet 4.6 or Auto. Do not default to Opus.
```

---

## 2. Requirements spec (paste as the build prompt)

### R1 — Confirm the starter agent runs
- Use the workshop starter agent unchanged; invoke it once.
- **Acceptance:** one invocation returns a response in eu-west-1.

### R2 — Observability: a readable trace
- Ensure the run emits an OpenTelemetry trace to AgentCore Observability → CloudWatch (via aws-opentelemetry-distro; no agent code changes).
- **Acceptance:** you can open one run and read session → trace → span (model call, tool call, decision).

### R3 — Governance: an observable policy denial
- Apply a Cedar policy with **default-deny**. Allow the starter agent's normal tool; DENY one privileged action.
- Trigger the denied action once (a scripted invocation is fine).
- **Acceptance:** the trace shows a deterministic **DENY**; nothing is mutated. *(This is the money moment — make it solid.)*

### R4 — Evaluation: deterministic + LLM-as-judge
- Configure AgentCore Evaluations with:
  - one **deterministic** grader — expected tool called AND RBAC enforced → pass/fail;
  - one **LLM-as-judge** — helpfulness or goal-success on a rubric → score + explanation.
- Run both on one recorded interaction.
- **Acceptance:** you can show a pass/fail plus a judge score with its explanation.

### R5 — (Optional) cost/latency glance
- Surface tokens, latency, and iteration count for the same run.
- **Acceptance:** visible on one screen; connects cost back to the morning's model-routing dimension.

### R6 — Capture the fallback pack (do this even if live works)
- Screenshot/export: the trace, the policy denial in the trace, and the eval result with judge explanation.
- Save to a local `demo-fallback/` folder.
- **Acceptance:** you could present the whole demo from static screens.

---

## 3. Build order (tonight)

1. R1 — starter agent runs, one clean invocation.
2. R2 — trace visible in Observability/CloudWatch.
3. **R3 — policy denial (highest value; get it solid).**
4. R4 — deterministic + judge eval.
5. R5 — optional cost/latency glance.
6. **R6 — capture the fallback pack, last, before you stop.**

## 4. Cut-list if time is short
- **Must-have:** R1, R2, R3 (invoke + trace + denial) — a strong 10–12 min operator walk-through on its own.
- **Nice-to-have:** R4 judge eval, R5 cost glance — capture as static screens if you can't get them live.

## 5. Ask Kiro to also produce
- A `demo-runsheet.md` listing, in order: invoke → open trace → show denial → show eval result.
- A short `README` with the exact commands you'll type on stage.
```
