# Restructuring AGENTS.md for an Agentic Flow

**Advisory note accompanying the sample QA review agents**

## Purpose

You already have a mature, single-prompt operating document (`AGENTS.md`) that
drives development and QA for ExampleApp. This note is our perspective on how
that same intent can be expressed as a set of focused, composable kiro-cli
agents — the pattern the sample configs demonstrate — and a phased path to get
there.

The sample agents we shared are a **starting point**, not a replacement for
`AGENTS.md`. They implement the standards-based *code review* core so your team
can feel the agentic workflow quickly. This document shows how the rest of
`AGENTS.md` maps onto the same pattern as you expand.

---

## Why move from one big prompt to many focused agents

`AGENTS.md` today is a single assistant that must disambiguate five processes,
carry every development standard, and hold the full output format for each
process — all in one context. That works, but as it grows it has some
predictable strains:

- **Context dilution.** One prompt holding five processes plus all standards
  means every run carries instructions it doesn't need. Focused agents load
  only what their job requires, which improves accuracy and lowers cost.
- **Everything is coupled.** A tweak to the QA report format risks the
  new-development flow; a change to one standard reverberates across every
  process. Separate agents isolate change.
- **No parallelism.** A single prompt reviews sequentially. An orchestrator
  can fan out specialist reviews in parallel, then aggregate — faster feedback
  on large diffs.
- **Consistency is hard to enforce.** Trigger-phrase disambiguation depends on
  the model choosing correctly each time. Distinct named agents make the
  choice explicit (`--agent qa-orchestrator`) and repeatable.
- **Standards drift.** Standards embedded in the prompt get copy-pasted and
  fork. Pointing every agent at one steering file
  (`development-standards.md`) gives a single source of truth that updates
  everywhere at once.

The agentic equivalent keeps the *content* of `AGENTS.md` but changes the
*packaging*: standards become steering, each process becomes an agent (or a
small orchestrator + specialists), and output formats live in the agent that
owns them.

---

## Mapping: AGENTS.md → agentic flow

| AGENTS.md element | Agentic equivalent | In the sample today |
|---|---|---|
| Section 2 — Development Standards | `development-standards.md` steering, referenced by every agent | **Shipped** — all specialists apply it |
| Process 1 — DEV QA Review (code analysis) | `qa-orchestrator` + 5 read-only specialists, parallel, aggregated report | **Shipped** (analysis core) |
| Process 1 — git mechanics (fetch/merge/merge-base diff) | Orchestrator variant granted scoped `git`/shell to compute the diff and merge state | Not yet — orchestrator asks for the changed-file list |
| Process 1 — functional testing (curl + PHP-FPM/Apache log scan) | A "runtime check" agent with scoped shell that runs the feature and greps error logs | Not yet |
| Process 1 — HTML `.log` report (exact structure, colors, tone, in-place strikethrough) | A dedicated "report formatter" agent that turns findings + prior notes into the required HTML | Not yet — output is a plain aggregated report |
| Process 2 — DEV QA Notes | A `dev-qa-notes` agent owning that HTML template | Not yet |
| Process 3 — New Development | A build agent (write + document); pairs with the review agents | Not yet (samples are review-only by design) |
| Process 4 / 5 — Share / Weekly Knowledge | A `knowledge` agent that dedups against the standards docs and writes `shared_knowledge_*` | Not yet |
| Process disambiguation / trigger phrases | Replaced by explicit agent selection (`--agent <name>`); an optional router agent can still map phrases to agents | Explicit selection today |
| Section 5 — Quality standards (no emojis, line numbers, new-code-only) | Folded into each agent's prompt + steering | Reflected in the review prompts |

---

## Gaps and how expanding the samples closes them

Each gap below is an incremental agent or capability — none require rebuilding
what exists.

1. **Auto-scoping to a diff.** Give an orchestrator variant `git` access
   (scoped to read-only git commands) so it runs
   `git diff $(git merge-base production HEAD)..HEAD` itself and reviews only
   `+` lines — matching AGENTS.md Step 4. Trade-off: this relaxes the strict
   read-only posture, so gate the shell permission deliberately.

2. **Functional testing + log scan.** Add a runtime-check agent with scoped
   shell to clear logs, exercise the feature via curl, and grep
   PHP-FPM/Apache logs, flagging new runtime errors as Critical — AGENTS.md
   Step 5.

3. **The exact QA report.** Add a report-formatter agent whose sole job is to
   render the required HTML `.log` (header block, color codes, issues nested
   under Implementation Notes, `JL {DATE}:` format, in-place strikethrough for
   resolved items, first-person tone) from the aggregated findings and the
   developer's HTML notes — AGENTS.md Step 3 and Step 7. Keeping this in its
   own agent means the format can evolve without touching the reviewers.

4. **HTML-notes intake with a mandatory stop.** Encode the "STOP and ask for
   HTML notes, preserve verbatim, append status lines" behavior in the
   formatter agent's prompt so notes are never rewritten.

5. **The other processes.** Add `dev-qa-notes`, a build agent for new
   development, and a `knowledge` agent for Share/Weekly Knowledge — each a
   small config mirroring the specialists' pattern, pointed at the same
   steering.

6. **Standards file alignment.** If your repo uses `newStandard.md` /
   `codingStandards.md` rather than `development-standards.md`, update the
   `resources` path in each agent to match — the pattern is identical.

---

## Suggested phased adoption

- **Phase 1 — Use it (today).** Run the sample `qa-orchestrator` on changed
  files, supplying the file list. Get the team comfortable with agent-driven
  review and the standards-as-steering model.
- **Phase 2 — Automate scope.** Add the git-enabled orchestrator variant so
  reviews self-scope to the branch diff.
- **Phase 3 — Match your output.** Add the report-formatter agent to produce
  your exact HTML `.log` and notes-handling behavior.
- **Phase 4 — Add runtime checks.** Add the functional-test/log-scan agent for
  full DEV QA Review parity.
- **Phase 5 — Cover the rest.** Add DEV QA Notes, New Development, and
  Knowledge agents, and (optionally) a small router that maps your existing
  trigger phrases to agent selection so muscle memory carries over.

Each phase is independently useful; nothing needs to wait for the whole set.

---

## Bottom line

`AGENTS.md` doesn't need to be discarded — its content is the raw material.
The agentic version keeps your standards and processes intact but repackages
them as steering + focused agents, which read more cleanly, run in parallel,
cost less per run, and are far easier to evolve. The sample is Phase 1; this
note is the map for Phases 2–5. We're happy to build any of these out with your
team.
