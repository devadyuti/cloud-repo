# AgentOps demo — presenter script
### Workshop slot 14:15–15:00 · "Operate & trust an agent"

This is what you **say and show**. The terminal commands live in
`demo-runsheet.md`; this script is the narration around them. Times are a guide
— protect the policy-denial moment (step 3) above all.

---

## 0 · Framing (before you touch anything) — ~2 min

> "This morning we *built* agents. The question every team hits next is the one
> that decides whether an agent ever reaches production: **once it's running,
> can you see what it's doing, stop it doing the wrong thing, and prove it's
> good?** That's AgentOps — the operations layer. I'm not going to build a new
> agent; I'm going to take an agent we already have and put the three things
> around it that let you actually trust it in production."

Put the three words on screen (or just say them) — this is the whole demo:
1. **Observability** — see what it did (traces).
2. **Governance** — stop the dangerous action, deterministically (policy).
3. **Evaluation** — prove quality, automatically (deterministic + judge).

> "Everything here is synthetic data in a sandbox account. The agent is
> deliberately trivial — a weather-and-calculator assistant — because the point
> isn't the agent, it's what we wrap around it."

---

## The agent we're observing (one slide / one breath)

> "Our agent runs on **Amazon Bedrock AgentCore Runtime**. It's a Strands agent
> on Claude Sonnet, with two tools: `weather` and a `calculator`. That's it.
> Now — three things I want to be able to do as the operator."

---

## 1 · Observability — "see what it did" — ~3 min

**Say:**
> "First, I invoke it — one normal request."

**Do:** `agentcore invoke "What is the weather in Athens?"` → *"…very sunny ☀️"*

**Say (while opening CloudWatch GenAI Observability):**
> "Nothing special about the answer. What matters is what got recorded. Every
> invocation emits an **OpenTelemetry trace** into CloudWatch — no code changes,
> the runtime does it. Here's this exact call."

**Show, tracing top-to-bottom on one trace:**
> "I can read the agent's whole thought process: it received the question →
> **called the model** → the model decided to **call the `weather` tool** → got
> the result → **produced the answer**. Every step, timed. This is the
> difference between 'the agent said something weird' and 'here's *exactly*
> where it went wrong.'"

**The cost/latency line (R5) — say while pointing at the span attributes:**
> "And on the same span I get the operational numbers: **tokens, latency,
> time-to-first-token, how many model calls**. This run was about 4.5 seconds,
> two model calls, ~4,000 tokens. That's your cost and latency per interaction —
> and it ties straight back to the model-routing conversation from this morning:
> a cheaper model on the simple turns cuts this bill directly."

**Transition:**
> "So I can *see* it. But seeing isn't enough — I need to *stop* it doing
> something dangerous."

---

## 2 · Governance — "stop the dangerous action" — ~4 min · **THE MONEY MOMENT**

**Set it up (this is the important framing):**
> "Here's the scenario every customer worries about: the agent has access to a
> **privileged tool** — say, issuing refunds. You do *not* want the model's
> judgment to be the only thing standing between a prompt and a $5,000 payout.
> So we put a **policy** in front of it — Cedar policy, enforced at the
> **gateway**, *outside* the agent's reasoning. The rule: refunds under $1,000
> are allowed; anything else is denied by default."

**Do — the allowed case first:**
> "Small refund, $500 — within policy."

`curl … "amount":500` → `{"status":"refunded", …}`

> "Allowed. The tool ran."

**Do — the denied case (slow down here):**
> "Now the same tool, same agent — but $5,000."

`curl … "amount":5000` → **`Tool Execution Denied … denied by default`**

**Say (let it land):**
> "**Denied.** And look at *why* — 'denied by default.' The policy engine made
> that call, not the model. The agent couldn't talk its way past it, couldn't be
> prompt-injected past it — the refund Lambda **never even ran**. This is
> deterministic governance: same input, same decision, every time, enforced
> outside the agent. *This* is what lets a security team sign off on an agent
> that can touch real systems."

**Transition:**
> "I can see it, I can constrain it. Last thing: can I *prove* it's actually
> good — at scale, without a human reading every transcript?"

---

## 3 · Evaluation — "prove it's good" — ~4 min

**Say:**
> "I'll grade that weather interaction two different ways — this is the pattern
> you'd run continuously in production, not by hand."

**Do:** `agentcore run eval --evaluator ToolAndPolicyCheck HelpfulnessJudge --session-id <id>`

**Show result 1 — deterministic:**
> "First, a **deterministic** check — plain code, zero tokens. It asks: did the
> agent actually call the `weather` tool for a weather question? **Pass.** This
> is your regression gate — it's cheap, it's exact, it never drifts. Run it on
> every deploy."

**Show result 2 — the judge:**
> "Second, an **LLM-as-a-judge** — for the fuzzy stuff code can't measure, like
> *was this actually helpful?* It scored **5 out of 5** and — crucially — it
> **explains why**: answered directly, used the right tool, accurate, clear. You
> get a quality signal *and* the reasoning, so you can trust the score."

**Say:**
> "Deterministic for the things that must be exactly right; a judge for the
> things that are subjective. Together, that's how you keep quality from
> silently regressing as prompts and models change."

---

## 4 · Close — ~1 min

> "So — three capabilities, all on an agent I didn't have to modify:
> **Observability** to see what it did, **Governance** to stop what it shouldn't
> do, and **Evaluation** to prove it's good. That's AgentOps. It's the layer
> that turns a promising demo into something you can actually run in production
> and put your name behind. The agent is easy — *operating and trusting* it is
> the work, and this is the toolkit for it."

---

## Anticipated questions (have these ready)

- **"Did you change the agent to get the traces?"**
  No — the tracing is on because it runs under AWS's OpenTelemetry distribution
  in the AgentCore runtime. No agent code changes; observability is a deploy-time
  concern, not an app concern.

- **"Is the policy the model deciding to refuse?"**
  No — that's the key point. It's a Cedar policy enforced at the gateway,
  completely outside the model. The model can't override it or be tricked past
  it. It's deterministic authorization, like IAM for tool calls.

- **"What if we want to watch a rule before enforcing it?"**
  Policy engines support a LOG_ONLY / shadow mode — you see what *would* be
  denied without blocking, then flip to ENFORCE when you're confident.

- **"Isn't LLM-as-judge just another model that can be wrong?"**
  Yes, which is why you pair it with deterministic checks for anything that must
  be exact, and you use the judge for subjective quality — and it gives you its
  reasoning so you can audit it. You can also calibrate the judge against
  human-labelled examples.

- **"Does this only work for Strands / this framework?"**
  No — AgentCore Observability, Policy, and Evaluations work across frameworks
  (LangGraph, CrewAI, etc.). We used Strands because that's the workshop agent.

- **"What does this cost to run?"**
  Traces are CloudWatch logs; the deterministic eval is a tiny Lambda (0 model
  tokens); only the judge makes a model call. You saw the per-run token/latency
  numbers in step 1 — that's the real operating cost, and it's observable.

---

## Safety nets
- If a live call fails, everything has a static capture in **`demo-fallback/`**
  (traces, the denial, the eval result) — pivot to those screens and keep the
  narrative going; the story doesn't depend on the network.
- Exact commands: **`demo-runsheet.md`**. Pre-materialize creds and run
  `agentcore status` **before** you walk on stage.
- If time gets tight: keep **invoke → trace → denial**. Show the eval and cost
  glance as static screens.
