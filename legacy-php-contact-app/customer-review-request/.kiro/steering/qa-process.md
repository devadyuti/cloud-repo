---
inclusion: manual
---
# QA, Code Review and Delivery Process

Load when reviewing a branch or PR, running the DEV QA self-check, writing ticket/QA notes, or working with git and the local dev environment. Domain rules being reviewed live in `php-standards.md`, `javascript-standards.md`, `html-css-standards.md` and `security-standards.md` — read the ones relevant to the diff.

---

## DEV QA Self-Check (Before Committing)

1. No `??` operator (PHP 5.6 fatal)
2. No `?->` operator (PHP 5.6 fatal)
3. Null-safe: no nullable vars passed to native string/array functions without wrapping
4. `php -l` passes on all modified files
5. No debug code (`console.log`, `var_dump`, `print_r`)
6. SQL inputs sanitized or prepared
7. `isset()` / `!empty()` before accessing `$_POST`/`$_GET` keys
8. Tabs for indentation, single quotes for strings
9. No changes to restricted folders
10. DB schema changes only in `db_structure/` files (and runtime ensure functions where applicable)
11. No investigation/data files (`.xlsx`, `.csv`, `.sql`, `:Zone.Identifier`) committed

---

## Issue Categories (Code Review)

| Severity | Examples |
|---|---|
| **Critical** | SQL injection, security vulnerabilities, fatal errors, data corruption, merge conflicts |
| **Major** | Deprecated functions, logic flaws, missing validation, PHP compatibility, `??` operator |
| **Minor** | Performance, code quality, maintainability |

**Never flag:** Missing trailing newlines, mixed line endings, whitespace/formatting inconsistencies.

**Only flag issues INTRODUCED by the branch being reviewed.** If a pattern existed in production and the branch left it unchanged, it is not an issue for that review.

---

## Standards Enforcement Scope

- These standards apply ONLY to **new code** being added. Minor changes to existing lines do not require rewriting surrounding code to comply.
- Coding and styling standard violations are **NEVER Critical** (unless they independently cause a fatal error or security vulnerability). They are:
  - **Major**: when the violation causes a functional problem, breaks theme compatibility, or creates a maintenance burden (inline colors themes can't override, duplicated code blocks, missing function comments on complex functions)
  - **Minor**: when the violation is cosmetic or a best-practice preference that doesn't affect functionality (spacing, px instead of em, missing comment on a simple function, pagination vs scroll-to-load choice)

---

## PR Review — 14 Standards

1. **SQL Injection Prevention** — prepared statements or proper sanitization; whitelist SQL identifiers; DB-sourced strings still `real_escape_string()`'d for syntax safety
2. **Authorization Checks** — trace full include chain for `checkAuthorised()`; new functionality needs NEW privileges; do not flag slider/iframe includes that rely on parent auth; flag any misplaced `$guest_access = true`
3. **PHP 5.6 / 8.5 Compatibility** — no `??`, no `?->`, no strict types, no deprecated/removed functions
4. **PHP 8.5 Null Safety** — safe wrappers, query result checks, variable initialization
5. **JavaScript Issues** — syntax errors, undefined references, load order, async misuse, reassigned `const`
6. **HTML Issues** — unclosed tags, column count mismatch, missing save handlers
7. **Input Sanitization** — `isset()` before access, correct sanitizer per type, no re-sanitization (`(int)` cast is acceptable)
8. **Dead Code and Debug Removal** — `console.log`, `var_dump`, unused variables, incomplete-refactor leftovers, dead cache arrays
9. **Defensive Coding Patterns** — explode safety, array_shift, config fallbacks, ob_clean rules, comma-wrapped config trap
10. **Query Result and Data Access** — SELECT coverage, result null-checks, redundant lookups
11. **Performance** — N+1 queries, missing indexes, uncached repeated calls (note: repeated `get_config()` is NOT a DB call)
12. **Coding Standards (Formatting)** — tabs, braces, naming, file headers
13. **CSS and Styling** — no inline styles, no px, no !important, theme colors in theme files
14. **Unrelated / Cosmetic Changes** — flag separately for awareness, not as issues

---

## Development & Review Practices

- **Merge-base diff for reviews**: always `git merge-base origin/<target> origin/<source>` then `git diff <merge-base>..origin/<source>`. Never use tip-to-tip (`<target>..<source>`) — it misreports target-only code as PR changes. Only flag issues introduced by the branch under review
- **Query timeout**: wrap investigative shell queries in `timeout` (10–30s); kill and refactor stuck queries; check `SHOW PROCESSLIST` for leftovers before retrying
- **OPcache awareness**: PHP-FPM caches compiled bytecode — after editing PHP files (or switching branches on localhost), restart FPM before testing, or code changes appear to have no effect (especially confusing for `db_defaults.php` / `function.php` changes that run on page load). Prefer `file_put_contents('/tmp/debug.log', ..., FILE_APPEND)` for reliable debug output
- **Merge conflict "Keep Both" strategy**: when a production-into-branch conflict is two independent features touching the same spot, keep BOTH blocks in a logical order rather than choosing one side. Verify the result with `php -l` and a merge-base diff (`git diff $(git merge-base production HEAD)..HEAD`) to confirm nothing else was lost
- **Never alter developer HTML notes in a QA report** — preserve the developer's notes character-for-character (full `<ul>` structure, inline styles, colours, links, videos). Even "condensing" or reformatting violates the rule. Only the report header changes; AI/QA findings are appended, never interleaved into or edited over the original notes
- **Re-QA must re-test the merge against the CURRENT production tip** — a branch that merged `production` at commit X is not permanently mergeable. Once production advances to Y, the same files re-conflict because the branch's merge-base is still X. On EVERY re-QA round, re-run `git fetch origin production:production` and re-test `git merge production` against the current tip. A prior clean merge does not carry forward; a re-conflict is still a blocking (CRITICAL) issue for that round even if the branch's own code is correct
- **Cross-ticket additive collisions recur until BOTH features reach production** — when two branches each add a column to the same table, insert an AJAX action after the same anchor, and change the same config-table header/`colspan`, they conflict on every merge until both land in production. Resolution is keep-both, but Git's auto-merge can silently DROP the other ticket's already-shipped feature. Always follow a production merge with a merge-base diff (`git diff $(git merge-base production HEAD)..HEAD`) and spot-check the other feature's columns/handlers/UI are still present. Coordinate merge ordering when multiple in-flight branches touch one hot config file
- **Pre-QA repo hygiene** — run `git status` before checking out a branch. If the working copy is mid-merge or mid-rebase (unmerged paths, detached HEAD), a `git checkout` will fail and forcing it discards in-progress conflict resolution. Stop and confirm intent before touching it; aborting is destructive and needs explicit confirmation. Only check out the QA branch once the tree is clean

- **Prompt & script impact check (review phase for `production` / `pre-production` / `product` targets)**: before approving a PR whose verdict is PASS or CONCERNS, scan the diff for changes that could break automation and scripted callers — (1) behaviour of URL endpoints that scripts POST to, (2) renamed/added/removed/retyped POST parameters on those endpoints, (3) schema changes to tables or columns referenced by direct queries in automation, (4) altered JSON/HTML response structures that scripts parse. Raise anything found for discussion before approval. This check does not change the verdict — it exists so automated processes do not break when the code goes live

### Mechanical Safe-Wrapper Audit (run after trace-based analysis)
After reasoning about the code, do a line-by-line grep of all changed/new code:

| Find | Must be | Native OK only if |
|------|---------|-------------------|
| `explode($delim, $var)` | `safe_explode(...)` | `$var` is a hardcoded string literal |
| `in_array($val, $arr)` | `safe_in_array(...)` | `$arr` is a hardcoded array literal |
| `implode($sep, $arr)` | `safe_implode(...)` | `$arr` is a hardcoded array literal |
| `count($var)` | `safe_count(...)` | `$var` is a hardcoded array literal |
| `array_filter($arr)` | `safe_array_filter(...)` | `$arr` is a hardcoded array literal |

For every `$_POST`/`$_GET` value expected to be an array, `isset()` alone is NOT sufficient — it must also have an `is_array()` check: `isset($_POST['k']) && is_array($_POST['k']) ? $_POST['k'] : []`.

---

## Critical Items — Never Remove Without Explicit Confirmation

During refactoring or optimization, the following categories were accidentally removed in the past and caused regressions. Before removing ANY code, run the pre-removal checklist below.

### General Pre-Removal Checklist
1. **Functions**: `grep -rn "function_name(" --include="*.php"` to confirm all callers before deleting a function
2. **`load_config()` defaults**: Verify a database default or setter exists that covers ALL customers before removing a hardcoded default — some defaults have NO other setter and removing them breaks every customer
3. **Fallback logic**: Check whether the `else`/fallback branch handles a real-world state (unconfigured customer, zero value, null) before collapsing it
4. **INSERT columns**: Check whether any caller passes that value in the `$details` array before dropping a column from an INSERT
5. **Template systems**: Check whether config keys (placeholder/label templates) are referenced in any customer's `general_configuration` before removing the template-application code
6. **Shared includes**: Never remove the `php8_compatibility_fixes.php` include from `shared_functions.php` (mobile geo-location app depends on it)

### High-Risk Patterns
- **Functions called from other files** (e.g. SQL-builder helpers used dozens of times across a tile) — a single deletion fatals every caller
- **`load_config()` defaults with no other setter** — the hardcoded default IS the only source of the value for new/unconfigured customers
- **Fallback logic for unconfigured state** — status/label defaults that return a sensible value when config is empty
- **Customer-facing template placeholders** — label templates with `[PLACEHOLDER]` replacements that customers actively configure
- **INSERT columns callers pass** — a column whose value defaults but is overridden by caller-supplied values that would otherwise be silently lost
- **Data-resolution fallbacks** — lookups that resolve a missing/zero id via a secondary table before writing

### Refactor Regression Check (mandatory on performance/restructure changes)
When a refactor replaces or restructures existing code, diff the old logic against the new logic line-by-line. Every behavioral filter, conditional skip, security gate, or visibility check in the original MUST still exist in the refactored version — specifically:
- `continue` statements inside loops that filter items
- Permission / security-level checks that gate visibility
- Array filters or `in_array()` guards that restrict displayed data

---

## Git & Version Control

- Commit messages describe what changed and why
- One logical change per commit — don't mix unrelated fixes
- Never commit debug code, commented-out blocks, or temporary test data
- **Never commit investigation/data files** — `.xlsx`, `.xls`, `.csv`, `.sql`, and Windows `:Zone.Identifier` metadata files. Flag any such files for removal before merge to production; they cause repo bloat and may contain customer data
- Don't push directly to main/master/production without confirmation
- Test changes locally before committing
- Base branch is always `production` (never `master`)
- CRLF line endings throughout — do not auto-convert (`git config --global core.autocrlf false`)
- **Branch naming:** `Ticket-{id}-{subject}-{INITIALS}` (LMP work uses `LMP-{id}-{subject}-{INITIALS}`)
- **Long-running feature branches:** after merging `production` into a branch that has been open a while, run a merge-base diff (`git diff <merge-base>..HEAD`) to confirm the merge did not silently drop another ticket's already-merged code. `git log production..HEAD | grep <sub#>` helps confirm which sub-tickets a long branch still contains

---

## Local Dev Environment (Reference)

- Local PHP runs 8.1; `error_reporting(0)` is set — runtime warnings are suppressed on-page, so check the PHP error log (`/var/log/php8.1_errors.log`) rather than relying on screen output
- `localhost:80` serves the feature branch under test; `localhost:81` serves the production baseline for side-by-side comparison
- PHP-FPM caches compiled bytecode — restart FPM after editing PHP files or switching branches, or changes appear to have no effect
- A lightweight unit-test harness exists at `AdminSettings/unit_tests.php`
- MySQL `sql_mode` should be empty locally to match production behaviour — a non-empty `sql_mode` (e.g. `ONLY_FULL_GROUP_BY`, `STRICT_TRANS_TABLES`) makes queries fail locally that run fine in production, producing false QA failures

---

## Documentation & Ticket Notes Standards

### Deliverable-Driven Structure (DOW)
All ticket documentation — dev notes, fix notes, completion notes, phase reviews — is structured around the ticket's Development Outcomes / Deliverables (DOW) bullets.

- **Every DOW bullet appears** as a top-level item. Verification-only items still get a short confirmation note ("Confirmed working — tested end-to-end"); none are silently dropped
- **Attribution on every note**: `{INITIALS} {YYYY-MM-DD}:` followed by the root cause, what was built or fixed, the files and lines touched, and how it works **within the system**. Describe system behaviour, never "satisfies requirement X" — detailed enough that another developer understands the fix without opening the code
- **Cross-cutting changes** are noted under each affected DOW bullet with a cross-reference, not filed under one bullet only

### HTML Notes — Hard Rules
Ticket notes are HTML living inside a TinyMCE editor. Notes are **appended** to the existing HTML, never regenerated. These rules are absolute.

1. **Never change existing content.** Every original note stays character-for-character — list structure, inline styles, colours, links, videos, wording. Condensing, reformatting, re-indenting or "tidying" the preparer's notes is a violation. Only the report header changes; new findings are appended, never interleaved into or edited over the original notes.

2. **Never change the existing formatting.** The document is a nested unordered list — keep it that way. Do not introduce block-level containers (a container div, a paragraph, a table, a section) and do not convert lists into blocks. Allowed tags are the ones already in use: unordered list, ordered list, list item, strong, em, span, code, horizontal rule, line break, anchor. Existing links and embedded videos are preserved as-is, never stripped.

3. **Never write an HTML element name in angle brackets — raw, escaped, or inside a code span.** TinyMCE decodes entities on round-trip, so an escaped tag becomes a live tag on save: it renders an actual widget in the ticket and corrupts that editor **and every other text editor on the page**. Escaping is not a mitigation. Name the element in words instead:

   | Never write (in angle brackets) | Write this |
   |---|---|
   | the select element | the dropdown |
   | the input element | the input field, the hidden field named `origin_business_name` |
   | the td element | the table cell |
   | the th element | the column header |
   | the script element | the script block |
   | the table / button / div / p / form / img / iframe elements | the table / the button / the container / the paragraph / the form / the image / the embedded frame |

   A code span is correct around **identifiers** — `get_donations_of_contact()`, `contacts_donation`, `donation_show_eyeball`, `Contacts/`, `class="donation_select_checkbox"`. It is never a workaround for an element name. No preformatted blocks and no code blocks anywhere in ticket HTML — code belongs in the Markdown plan file.

4. **Indent and nest the summary of changes** consistently, three levels: attribution heading (`{INITIALS} {YYYY-MM-DD}:`) → file path → one bullet per change. No walls of text, no mixed indentation, no repeated headings for the same file.

**Mechanical gate:** run the notes format check script against any HTML notes file before delivering it. It fails on display element names in angle brackets (raw, escaped or code-wrapped), block-level containers, preformatted blocks, stray self-closing markup, and unbalanced list nesting.
