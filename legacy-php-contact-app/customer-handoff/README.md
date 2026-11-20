# Agent-Driven Code Review — Sample Configs

A small, working example of a multi-agent PHP code review for kiro-cli. An
orchestrator agent delegates to 5 read-only specialist agents in parallel;
each reviews your code against your own `development-standards.md` and reports
findings, and the orchestrator aggregates everything into one PASS/FAIL
report.

These are **starter samples** — read them, run them, then extend them as your
team builds expertise.

---

## What's in here

This mirrors the exact `.kiro/` folder structure to maintain in your project:

```
customer-handoff/
├── README.md                         ← this file
└── .kiro/
    ├── agents/
    │   ├── qa-orchestrator.json       ← entry point: delegates + aggregates
    │   ├── qa-php-compat.json         ← PHP 5.6/8.5 compatibility + null safety
    │   ├── qa-security.json           ← SQL injection, input validation, secrets
    │   ├── qa-code-quality.json       ← naming, formatting, comments, debug code
    │   ├── qa-frontend.json           ← JavaScript, CSS, HTML, UI/UX
    │   └── qa-process.json            ← PR checklist, DEV QA self-check, git hygiene
    └── steering/
        └── development-standards.md   ← YOUR coding standards (you supply this)
```

> The `steering/` folder here ships with a placeholder `.txt` only. Drop your
> real `development-standards.md` into `.kiro/steering/` (you likely already
> maintain it) and delete the placeholder.

## Prerequisites

- `kiro-cli` installed and authenticated.
- Your repo has `.kiro/steering/development-standards.md` (your coding
  standards). The agents load this as their single source of truth.
- The model set in each agent (`claude-opus-4.6`) is available to your
  account. Change it if you prefer a different one (see "Model", below).

## Install

Copy the `.kiro/` contents into your repo (merges with your existing `.kiro/`):

```
cp -R customer-handoff/.kiro/agents/*.json <your-repo>/.kiro/agents/
```

Make sure your `development-standards.md` is at
`<your-repo>/.kiro/steering/development-standards.md` (the placeholder `.txt`
in the sample marks the spot — you don't copy that).

Your layout should end up as:

```
<your-repo>/
├── .kiro/
│   ├── agents/                 ← the 6 files above
│   └── steering/
│       └── development-standards.md
└── ... your PHP source ...
```

The first time you run a project agent, kiro-cli asks you to trust the
workspace — approve it.

## Run

Run **from your repo root** (where `.kiro/` lives) and name the files you
want reviewed — typically the files changed for a ticket:

```
kiro-cli chat --agent qa-orchestrator -a "Run a full code review on path/to/File1.php path/to/File2.php"
```

- `-a` trusts tools so the read-only agents don't prompt on every read.
  Drop it if you'd rather confirm each step.
- Add `--no-interactive` for a scripted, one-shot run (e.g. in CI or a
  wrapper script).
- You can also scope by folder, e.g. `"... review the PHP files under
  Contacts/"` — the orchestrator will enumerate `*.php` under that path.

### Scoping

The orchestrator reviews exactly what you tell it:

1. **Named files** — reviews those files.
2. **A folder/tile** — enumerates `*.php` under it.
3. **"this branch" / "the diff" with no file list** — it will ask you for
   the changed files, because the agents are read-only and cannot run git
   themselves. Supply the list (e.g. from `git diff --name-only`), or paste
   the diff.

If you don't scope it, it will try to review everything you point it at — so
scope to the ticket's changed files for fast, relevant results.

---

## How it works

1. You invoke `qa-orchestrator`.
2. It dispatches all 5 specialists **in parallel**, each with the same file
   list, each restricted to its own domain of `development-standards.md`.
3. Each specialist finishes with a verdict line: `PASS` or `NEEDS_CHANGES`.
4. **Feedback loop**: any specialist that returns `NEEDS_CHANGES` is re-run
   (up to 3 attempts per domain). These agents are reviewers, not fixers —
   the loop lets a developer fix issues and re-run without restarting the
   whole review.
5. The orchestrator prints one aggregated report: a per-domain PASS/FAIL
   summary table, all findings grouped by domain and file (file, line,
   severity, rule, suggested fix), and an overall verdict.

### Design choices worth knowing

- **Read-only by design.** Every agent lists only `read` (the orchestrator
  also has `subagent`) and explicitly excludes all write/shell tools. The
  review never edits your code.
- **One source of truth.** All agents point at
  `file://.kiro/steering/development-standards.md`. Update that file and every
  agent's behavior updates with it — no need to touch the agent JSON.
- **Trusted sub-agents.** The orchestrator lists the 5 specialists under
  `toolsSettings.subagent.trustedAgents`, so delegation runs without extra
  prompts.

## Model

Each file pins `"model": "claude-opus-4.6"` so every developer and QA machine
runs the same model and gets consistent results. To change it, edit the
`model` field in **all 6 files** (sub-agents run under their own config's
model, not the orchestrator's). Use `kiro-cli chat --list-models` to see valid
IDs. Setting `"auto"` lets Kiro pick per task (cheaper, less consistent).

> Note on consistency: pinning the model removes routing drift, so results are
> highly stable across machines — but LLM output is not byte-for-byte
> deterministic. Treat this as a strong, consistent first-pass reviewer, not a
> deterministic linter that proves every rule on every line.

## Extending this

Some natural next steps as you gain expertise:

- **Add a specialist.** Copy one of the `qa-*.json` files, point its prompt at
  a different section of `development-standards.md` (e.g. performance / N+1
  queries), then add its name to the orchestrator's `availableAgents` and
  `trustedAgents`, and mention it in the orchestrator prompt.
- **Auto-scope to a diff.** Give the orchestrator `execute_bash` limited to
  git so it can compute the changed-file list itself instead of asking. This
  trades the strict read-only guarantee for convenience — decide per your risk
  tolerance.
- **Split your standards into focused steering files.** Instead of one large
  `development-standards.md`, you can split it into per-domain files with
  inclusion rules so each specialist loads only what it needs. (Note: on
  kiro-cli all steering files load regardless of inclusion mode.)
- **Tune severities and scope.** The prompts follow the "only flag issues
  introduced by the change" rule and your severity tables — adjust the prompts
  as your review conventions evolve.
- **Capture output to the ticket** for auditability, since findings are
  consistent but not bit-identical run to run.

## Troubleshooting

- **`unrecognized subcommand '...'`** — the prompt must go through the `chat`
  subcommand: `kiro-cli chat --agent qa-orchestrator "..."` (not
  `kiro-cli --agent ... "..."`).
- **Agent not found** — confirm the files are in `<repo>/.kiro/agents/` and
  you're running from the repo root; check `kiro-cli agent --help`.
- **Steering seems ignored** — confirm
  `.kiro/steering/development-standards.md` exists at the root you run from;
  the agents' `resources` path is relative to that root.
- **Model error** — the pinned model isn't available to your account; run
  `kiro-cli chat --list-models` and set an available ID in all 6 files.
