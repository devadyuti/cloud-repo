---
inclusion: manual
---

# PR Review — 14 Standards

1. **SQL Injection Prevention** — prepared statements or proper
   sanitization; whitelist SQL identifiers; DB-sourced strings still
   `real_escape_string()`'d for syntax safety.
2. **Authorization Checks** — trace full include chain for
   `checkAuthorised()`; new functionality needs NEW privileges; do not flag
   slider/iframe includes that rely on parent auth; flag any misplaced
   `$guest_access = true`.
3. **PHP 5.6 / 8.5 Compatibility** — no `??`, no `?->`, no strict types, no
   deprecated/removed functions.
4. **PHP 8.5 Null Safety** — safe wrappers, query result checks, variable
   initialization.
5. **JavaScript Issues** — syntax errors, undefined references, load order,
   async misuse, reassigned `const`.
6. **HTML Issues** — unclosed tags, column count mismatch, missing save
   handlers.
7. **Input Sanitization** — `isset()` before access, correct sanitizer per
   type, no re-sanitization (`(int)` cast is acceptable).
8. **Dead Code and Debug Removal** — `console.log`, `var_dump`, unused
   variables, incomplete-refactor leftovers, dead cache arrays.
9. **Defensive Coding Patterns** — explode safety, array_shift, config
   fallbacks, comma-wrapped config trap.
10. **Query Result and Data Access** — SELECT coverage, result null-checks,
    redundant lookups.
11. **Performance** — N+1 queries, missing indexes, uncached repeated calls
    (note: repeated `get_config()` is NOT a DB call).
12. **Coding Standards (Formatting)** — tabs, braces, naming, file headers.
13. **CSS and Styling** — no inline styles, no px, no !important, theme
    colors in theme files.
14. **Unrelated / Cosmetic Changes** — flag separately for awareness, not
    as issues.

---

# DEV QA Self-Check (Before Committing)

1. No `??` operator (PHP 5.6 fatal)
2. No `?->` operator (PHP 5.6 fatal)
3. Null-safe: no nullable vars passed to native string/array functions
   without wrapping
4. `php -l` passes on all modified files
5. No debug code (`console.log`, `var_dump`, `print_r`)
6. SQL inputs sanitized or prepared
7. `isset()` / `!empty()` before accessing `$_POST`/`$_GET` keys
8. Tabs for indentation, single quotes for strings
9. No changes to restricted folders
10. DB schema changes only in `db_structure/` files (and runtime ensure
    functions where applicable)
11. No investigation/data files (`.xlsx`, `.csv`, `.sql`,
    `:Zone.Identifier`) committed

---

# Standards Enforcement Scope

- These standards apply ONLY to **new code** being added. Minor changes to
  existing lines do not require rewriting surrounding code to comply.
- Coding and styling standard violations are **NEVER Critical** (unless
  they independently cause a fatal error or security vulnerability).
- **Only flag issues INTRODUCED by the branch being reviewed.** If a
  pattern existed before the change and the change left it unchanged, it is
  not an issue for that review.

---

# Git & Version Control

- Commit messages describe what changed and why.
- One logical change per commit — don't mix unrelated fixes.
- Never commit debug code, commented-out blocks, or temporary test data.
- **Never commit investigation/data files** — `.xlsx`, `.xls`, `.csv`,
  `.sql`, and Windows `:Zone.Identifier` metadata files.
- Don't push directly to main/master/production without confirmation.
- Test changes locally before committing.
- CRLF line endings throughout — do not auto-convert.

---

# Restricted Folders (Never Modify)

Never make changes in submodules or these folders:
`lib`, `PHPExcel`, `php-excel-reader`, `tcpdf`, `fpdi2`, `fpdf181`,
`FPDI-1.6.1`, `mrbs`, `oauth-php`, `swiftmailer-5.x`,
`swiftmailer-calendar-master`, `tinymce`, `tinymce_5.0.6`, `tinymce_7.0.1`.

---

# Full QA Checklist (for qa-orchestrator use)

When running a full QA pass, aggregate all five specialist domains
(PHP compatibility, security, code quality, frontend, process) into a
single PASS/FAIL report per domain, following the 14 standards above.
Re-run any domain that reports `NEEDS_CHANGES` until it reports `PASS` or
the maximum retry count is reached.
