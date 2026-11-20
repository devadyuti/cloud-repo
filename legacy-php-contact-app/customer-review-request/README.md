# Agent-Driven Code Review — Split-Steering Setup

A working multi-agent PHP code review for kiro-cli, wired to a **domain-split
steering set**. An orchestrator delegates to 5 read-only specialist agents in
parallel; each reviews your code against the steering file(s) for its domain
and reports findings, and the orchestrator aggregates everything into one
PASS/FAIL report.

This setup pairs the sample review agents with a steering layout that has been
split by topic (only `essentials.md` loads on every interaction; the rest load
on demand). The agents have been repointed to the split files accordingly.

---

## What's in here

```
.kiro/
├── agents/
│   ├── qa-orchestrator.json       ← entry point: delegates + aggregates
│   ├── qa-php-compat.json         ← PHP 5.6/8.5 compatibility + null safety
│   ├── qa-security.json           ← SQL injection, input validation, secrets
│   ├── qa-code-quality.json       ← naming, formatting, comments, debug code
│   ├── qa-frontend.json           ← JavaScript, CSS, HTML, UI/UX
│   └── qa-process.json            ← PR checklist, DEV QA self-check, git hygiene
└── steering/
    ├── essentials.md              ← always-on: non-negotiables, naming, code quality, debug, restricted folders
    ├── product.md                 ← always-on
    ├── structure.md               ← always-on
    ├── tech.md                    ← always-on
    ├── php-standards.md           ← PHP compat, null safety, SQL/DB, defensive patterns
    ├── security-standards.md      ← SQL injection, input validation, auth, uploads
    ├── javascript-standards.md    ← jQuery, AJAX, client-side
    ├── html-css-standards.md      ← HTML, CSS, UI/UX, scrolling, PDF
    ├── qa-process.md              ← DEV QA self-check, PR review, severity, git, docs
    ├── architecture-patterns.md   ← platform wiring (reference, manual)
    ├── module-knowledge.md        ← per-tile internals (reference, manual)
    └── development_standards.md   ← superseded monolith, kept as reference only
```

## Which agent reads which steering file

`essentials.md` (plus `product.md` / `structure.md` / `tech.md`) is always
loaded, so the universal rules reach every agent. Each specialist additionally
pins the domain file(s) it needs:

| Agent | Pinned steering |
|---|---|
| `qa-orchestrator` | `essentials.md` + `qa-process.md` (severity / issue categories) |
| `qa-php-compat` | `php-standards.md` |
| `qa-security` | `security-standards.md` |
| `qa-code-quality` | `essentials.md` + `qa-process.md` |
| `qa-frontend` | `javascript-standards.md` + `html-css-standards.md` |
| `qa-process` | `qa-process.md` |

## Prerequisites

- `kiro-cli` installed and authenticated.
- The steering set above lives at `.kiro/steering/` in the repo you run from.
- The model pinned in each agent (`claude-opus-4.6`) is available to your
  account. Change it if you prefer a different one (see "Model", below).

## Run

Run **from your repo root** (where `.kiro/` lives) and name the files you want
reviewed — typically the files changed for a ticket:

```
kiro-cli chat --agent qa-orchestrator -a "Run a full code review on path/to/File1.php path/to/File2.php"
```

- `-a` trusts tools so the read-only agents don't prompt on every read. Drop it
  if you'd rather confirm each step.
- Add `--no-interactive` for a scripted, one-shot run (e.g. in CI or a wrapper
  script).
- You can also scope by folder, e.g. `"... review the PHP files under
  Contacts/"` — the orchestrator will enumerate `*.php` under that path.

### Scoping

The orchestrator reviews exactly what you tell it:

1. **Named files** — reviews those files.
2. **A folder/tile** — enumerates `*.php` under it.
3. **"this branch" / "the diff" with no file list** — it will ask you for the
   changed files, because the agents are read-only and cannot run git
   themselves. Supply the list (e.g. from `git diff --name-only`), or paste the
   diff.

Scope to the ticket's changed files for fast, relevant results.

---

## How it works

1. You invoke `qa-orchestrator`.
2. It dispatches all 5 specialists **in parallel**, each with the same file
   list, each reviewing strictly within its own domain against its steering
   file(s).
3. Each specialist finishes with a verdict line: `PASS` or `NEEDS_CHANGES`.
4. **Feedback loop**: any specialist that returns `NEEDS_CHANGES` is re-run
   (up to 3 attempts per domain). These agents are reviewers, not fixers — the
   loop lets a developer fix issues and re-run without restarting the whole
   review.
5. The orchestrator prints one aggregated report: a per-domain PASS/FAIL
   summary table, all findings grouped by domain and file (file, line,
   severity, rule, suggested fix), and an overall verdict.

### Design choices worth knowing

- **Read-only by design.** Every agent lists only `read` (the orchestrator also
  has `subagent`) and explicitly excludes all write/shell tools. The review
  never edits your code.
- **Steering split by domain.** Each specialist pins the file(s) for its area
  (see the table above); `essentials.md` carries the always-on baseline. Update
  a domain file and that specialist's behavior updates with it — no need to
  touch the agent JSON. Severity/issue definitions live in `qa-process.md`.
- **Trusted sub-agents.** The orchestrator lists the 5 specialists under
  `toolsSettings.subagent.trustedAgents`, so delegation runs without extra
  prompts.

> Note: on kiro-cli, steering inclusion modes are not honored — all files in
> `.kiro/steering/` load regardless of `always`/`manual`. The per-agent
> `resources` pins still matter: they document each agent's true dependency and
> guarantee the right domain file is in context (and are honored in the IDE,
> where inclusion modes do apply).

## Model

Each file pins `"model": "claude-opus-4.6"` so every developer and QA machine
runs the same model and gets consistent results. To change it, edit the `model`
field in **all 6 files** (sub-agents run under their own config's model, not
the orchestrator's). Use `kiro-cli chat --list-models` to see valid IDs.
Setting `"auto"` lets Kiro pick per task (cheaper, less consistent).

> Note on consistency: pinning the model removes routing drift, so results are
> highly stable across machines — but LLM output is not byte-for-byte
> deterministic. Treat this as a strong, consistent first-pass reviewer, not a
> deterministic linter that proves every rule on every line.

## Extending this

- **Add a specialist.** Copy one of the `qa-*.json` files, point its `resources`
  and prompt at the relevant steering file (e.g. a performance/N+1 agent on
  `php-standards.md`), then add its name to the orchestrator's `availableAgents`
  and `trustedAgents`, and mention it in the orchestrator prompt.
- **Auto-scope to a diff.** Give the orchestrator `execute_bash` limited to git
  so it can compute the changed-file list itself instead of asking. This trades
  the strict read-only guarantee for convenience — decide per your risk
  tolerance.
- **Keep the map current.** When you add or rename a steering file, update the
  affected agent's `resources` and the mapping table above.
- **Tune severities and scope.** The prompts follow the "only flag issues
  introduced by the change" rule and the severity table in `qa-process.md` —
  adjust as your review conventions evolve.
- **Capture output to the ticket** for auditability, since findings are
  consistent but not bit-identical run to run.

## Troubleshooting

- **`unrecognized subcommand '...'`** — the prompt must go through the `chat`
  subcommand: `kiro-cli chat --agent qa-orchestrator "..."` (not
  `kiro-cli --agent ... "..."`).
- **Agent not found** — confirm the files are in `<repo>/.kiro/agents/` and
  you're running from the repo root; check `kiro-cli agent --help`.
- **Steering seems ignored** — confirm the steering files exist at
  `.kiro/steering/` at the root you run from; each agent's `resources` paths
  are relative to that root. If you rename a file, update the agents that pin
  it.
- **Model error** — the pinned model isn't available to your account; run
  `kiro-cli chat --list-models` and set an available ID in all 6 files.
