Subject: QA code-review agents — sample configs + notes on model choice & result consistency

Hi [Name],

As promised, attached is `qa-review-agents-handoff.zip` — a working set of sample agent configurations for running an automated, standards-based PHP code review through kiro-cli. It's a QA orchestrator that delegates to five read-only specialist agents (PHP compatibility, security, code quality, frontend, and process), each reviewing against your own `development-standards.md`. The README walks through install, the run command, how it works, and how to extend it.

The intent here is to give your team a hands-on starting point for building and reviewing quickly with an AI assistant — something you run today and then grow. It is deliberately focused on the standards-based code-review core, not a full replacement for your existing process prompt.

I've also included a short advisory note, `AGENTS-agentic-flow-advisory.md`, with our perspective on how your current `AGENTS.md` could be restructured into an agentic flow like this sample — a mapping of its processes to focused agents, the gaps between the sample and the full workflow, and a phased path to close them by expanding the same pattern. Worth a read alongside the sample.

Before your team rolls it out, two characteristics are worth setting expectations on.

1. Model choice — a consistency vs. cost trade-off

The agents are pinned to `claude-opus-4.6` to match your current setting, so every developer and QA machine runs the same model and produces comparable results. A few things to know:

- Pinning improves consistency but costs more. Opus is a higher-tier (roughly 2.2x credit) model, and each review fans out to five specialists in parallel — plus automatic re-runs on any domain that still has issues. So a full review consumes credits noticeably faster than the default "auto" setting.
- It's your call to tune. You can switch to a lighter model or to "auto" (which lets the tool pick per task) to reduce cost, at the expense of some cross-machine consistency. If you change it, set the model in all six agent files — each specialist runs under its own config, not the orchestrator's.
- Availability depends on your account. Whichever model you pin must be enabled for the accounts your team uses.

2. LLM output is consistent in substance, not word-for-word identical

This is an AI-driven review, not a deterministic linter, so please frame it to the team accordingly:

- Across machines and repeated runs, you'll get consistent findings and severities — the same issues flagged against the same standards — but not byte-for-byte identical comment text. Wording will vary, and an occasional borderline finding may appear in one run and not another.
- Pinning the model (above) removes model-routing drift and makes results markedly more stable, but it does not eliminate the natural sampling variability inherent to LLMs.
- Best treated as a strong, repeatable first-pass reviewer that applies your standards consistently — complementing human review, not a gate that proves every rule on every line.

To get the most consistent experience, we'd recommend: keep everyone on the same version of the configs, run from the repository root, scope each review to the ticket's changed files, and capture the output into the ticket for traceability.

These are intentionally a starting point — the README includes ideas for extending them (adding specialists, auto-scoping to a diff, splitting your standards into focused steering files) as your team builds expertise. The advisory note lays out a phased roadmap (Phase 1 is what's in the zip; Phases 2–5 add diff auto-scoping, your exact report format, functional/log checks, and the remaining processes).

Happy to walk through it live, or to build out any of those phases with your team.

Best regards,
[Your name]
