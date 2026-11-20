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
