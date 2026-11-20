# Feature Spec: Kiro Code Review Agent for Legacy PHP

## Objective

Build a **code review agent with sub-agents** that uses `development-standards.md` as its steering source to automatically review legacy PHP code for security, code quality, PHP 5.6/8.5 compatibility, styling, and coding standards. The orchestrator delegates to 5 specialist sub-agents running in parallel with feedback loops.

A sample legacy PHP contact list app (2-3 pages) is included as a **mock project** to validate the agents work. The app itself is not the deliverable — the agent setup is.

**Final deliverable:** A `.kiro/` folder (agents + steering + hooks) that can be dropped into any legacy PHP repo to run consistent, repeatable code review across all developers.

## Prompt for Kiro

Create a Kiro code review agent with sub-agents using `development-standards.md` as the source of truth. Split it into focused steering files, build a QA orchestrator + 5 specialist sub-agents that review PHP code against those standards in parallel. Include a mock legacy PHP contact list app with intentional bugs to validate the agents catch real issues.

**The final deliverable** is a `.kiro/` folder containing:

- Steering files (split from development-standards.md with proper inclusion directives)
- A QA orchestrator agent that delegates to 5 specialist sub-agents in parallel
- A feedback loop — each sub-agent re-runs until all checks pass
- A code review hook that triggers on file save

All configs are checked into the repo so every developer and QA member gets the same agent behaviour.

---

## Phase 1: Mock PHP App (Test Target Only)

Build a 2-3 page legacy PHP contact list app. Flat files, no framework, mixed PHP/HTML/CSS/JS in same files, procedural, jQuery for AJAX, Apache + MySQL.

### Intentional Issues to Embed

- SQL injection (string concatenation in queries)
- PHP 8.5 null safety (explode/count/trim on nullable vars without safe wrappers)
- Hardcoded credentials in db_connect.php
- Missing isset() on $_GET/$_POST
- Loose comparison (0 == "string")
- Debug code left in (var_dump, console.log)
- CSS !important overuse
- Missing AJAX error handlers
- Deprecated functions (FILTER_SANITIZE_STRING)

### Files

```
project/
├── index.php              — Dashboard (contact count, recent activity)
├── contacts.php           — Full CRUD (add/edit/delete), inline form
├── ajax_handler.php       — Handles AJAX requests
├── db_connect.php         — MySQL connection (mysqli)
├── shared_functions.php   — safe_* wrapper functions
└── development-standards.md  — Full standards file (SOURCE for steering split)

```

### Database

```sql
CREATE TABLE contacts (
    contactid INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(200),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted INT(1) DEFAULT 0
);

```

---

## Phase 2: Code Review Agent Setup (Primary Objective)

### Step 1: Split development-standards.md into steering files

| File | Inclusion | Description | Content |
| --- | --- | --- | --- |
| `product.md` | `always` (~500 tokens) | Platform overview | "ExampleApp is a legacy PHP platform, Apache + MySQL, no framework" |
| `tech.md` | `always` (~500 tokens) | Lock in versions | PHP 5.6+8.5, MySQL via mysqli, jQuery, ES5 JS, no Composer |
| `php-standards.md` | `always` (~2000 tokens) | PHP compat rules | Null coalescing prohibition, safe_* wrappers, removed functions, polyfills |
| `security-standards.md` | `auto` | Security review | SQL parameterisation, input sanitisation, auth checks, file uploads |
| `javascript-standards.md` | `auto` | JS/AJAX review | camelCase, error handlers, URL encoding, no ES6 |
| `css-html-standards.md` | `auto` | CSS/HTML review | No !important, class selectors, responsive, accessible |
| `code-quality.md` | `auto` | Code quality | snake_case PHP, full words, docstrings, no debug code, comments |
| `qa-process.md` | `manual` | QA checklist | Full QA steps, PR 14 standards |

### Step 2: Create QA Orchestrator Agent

`.kiro/agents/qa-orchestrator.json`:

- model: auto
- tools: includes `subagent`
- Delegates to 5 specialist sub-agents in parallel
- Aggregates results into a final PASS/FAIL report
- Review loop: re-runs any FAILED agents (trigger: "NEEDS_CHANGES", max 3 iterations)
- toolsSettings.subagent.trustedAgents: all 5 sub-agents

### Step 3: Create 5 QA Sub-Agents

Each sub-agent gets ONLY the steering relevant to its domain (based on actual content analysis of development-standards.md):

- model: auto
- tools: readFile, readMultipleFiles, listDirectory, grep, glob (read-only)
- Prompt includes feedback loop: "Run all checks. If any CRITICAL issues remain, output NEEDS_CHANGES. Repeat until all PASS or max iterations reached."

| Agent | Steering Sections (from development-standards.md) | ~Tokens | Reviews For |
| --- | --- | --- | --- |
| `qa-php-compat.json` | PHP Compatibility Requirements + Defensive Coding Patterns | ~5,400 | PHP 5.6/8.5 null safety, safe_* wrappers, deprecated/removed functions, polyfills, loose comparisons |
| `qa-security.json` | Security Standards + Database & SQL Standards + MySQL Login Functions | ~4,700 | SQL injection, parameterised queries, input validation, auth checks, file uploads, hardcoded secrets |
| `qa-code-quality.json` | Naming Conventions + Code Quality + Error Handling + Debug Code + Development & Review + Documentation Standards | ~4,600 | snake_case, comments, dead code, debug removal (var_dump/console.log), function length, ticket docs |
| `qa-frontend.json` | JavaScript Standards + CSS Standards + HTML Standards + UI/UX Style Guide + Scrolling Rules | ~3,400 | camelCase JS, AJAX error handlers, URL encoding, no ES6, no !important, class selectors, responsive |
| `qa-process.json` | PR Review 14 Standards + DEV QA Self-Check + Standards Enforcement + Git & Version Control + Restricted Folders | ~1,500 | Process compliance — commit standards, restricted folders, PR checklist, review scope |

**Always-on steering (loaded by ALL agents via .kiro/steering/):**

- `product.md` (~500 tokens) — platform overview
- `tech.md` (~500 tokens) — PHP 5.6+8.5, MySQL, jQuery, no framework (VERSION LOCK)
- `php-core.md` (~1,500 tokens) — most critical PHP compat rules (subset of full php-compat)

**Manual inclusion (reference only — not loaded by default):**

- `module-architecture.md` (~10,400 tokens) — all module-specific architecture docs (invoke with #module-architecture)
- `platform-config.md` (~4,700 tokens) — platform config, multi-flag, tax, theme, API systems (invoke with #platform-config)

### Step 4: Create Code Review Hook

`.kiro/hooks/code-review.kiro.hook`:

```
On file save in *.php:
1. Check for PHP 8.5 null safety issues (explode/count/trim on nullable without safe_*)
2. Check for hardcoded credentials or API keys
3. Check for debug code (var_dump, print_r, console.log with test data)
4. Report findings inline with file and line reference.

```

---

## Phase 3: Validate

Run: `kiro-cli --agent qa-orchestrator "Run full QA code review on this project using development-standards.md"`

Expected outcome:

- All 5 sub-agents execute in parallel
- Each finds the intentional issues in the sample PHP app
- Feedback loop re-runs any FAILED agents
- Final report: aggregated findings with PASS/FAIL per domain
- Demonstrates that development-standards.md is being applied consistently via split steering

---

## Tasks

- [ ] Task 1: Create db_connect.php (hardcoded creds — intentional)
- [ ] Task 2: Create shared_functions.php (safe_* wrappers)
- [ ] Task 3: Create contacts.php (mixed PHP/HTML/CSS/JS, null safety issues, loose comparisons)
- [ ] Task 4: Create ajax_handler.php (SQL injection, missing validation — intentional)
- [ ] Task 5: Create index.php (debug code, deprecated functions — intentional)
- [ ] Task 6: Split development-standards.md → .kiro/steering/ (8 files with correct inclusion modes)
- [ ] Task 7: Create .kiro/agents/qa-orchestrator.json (orchestrator with subagent delegation)
- [ ] Task 8: Create .kiro/agents/qa-*.json (5 sub-agents with feedback loops)
- [ ] Task 9: Create .kiro/hooks/code-review.kiro.hook
- [ ] Task 10: Run qa-orchestrator and verify all agents find the intentional issues

