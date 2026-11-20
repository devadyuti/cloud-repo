---
inclusion: auto
name: code-quality
description: Code quality standards for PHP — naming conventions, formatting, comments, debug-code removal, error handling, and documentation. Use when reviewing PHP code for style, maintainability, or dead/debug code.
---

# Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Variables | snake_case (full words) | `$contact_name` |
| Functions (PHP) | snake_case (full words) | `get_contact_data()` |
| Functions (JS) | camelCase (short words) | `overlayIFrameSlider()` |
| Constants | UPPERCASE with underscores | `DATABASE_NAME` |
| Database tables | singular, lowercase + underscores | `contact_field` |
| Database fields | lowercase with underscores | `contact_fields` |
| File names | underscore-separated lowercase | `edit_tickets.php` |
| JS functional selectors | underscore-separated classes | `_save_button` |
| CSS styling selectors | dash-separated classes | `save-button` |

- Column names cannot use MySQL keywords (`order`, `int`, `date`, `time`,
  `datetime`).
- HTML `id` attributes should not be used — reference elements by class,
  type, and relative position.

---

# Code Quality Standards

## Clean Code
- Code should be self-documenting with clear variable and function names.
- Never duplicate code — pass variables to a shared function or include a
  shared file.
- Tabs for indentation (at the start of the line).
- Opening brace on same line (functions, if blocks).
- Single quotes for PHP strings; double quotes for MySQL queries.
- One statement per line — never more than one.
- One space after commas and control characters (closing parens,
  ampersands, semicolons); no double spaces; no trailing whitespace.
- No space after open parens or before `{ } [ ] ( )` (unless immediately
  preceded by a control character).
- Maximum 1 blank line between blocks.
- No mid-line alignment with spaces.
- Files that are entirely PHP: no closing `?>`.
- Keywords/system constants (`true`, `false`, `null`, `const`) lowercase;
  defined constants UPPERCASE.
- Group `if / else` rather than subsequent independent `if` conditionals
  where possible.

## Comments
- Comment at least each function (purpose + each parameter).
- Comment most conditional / switch / loop blocks, and non-obvious
  lines/variables.
- Comments ≥ 3 lines use `/* block */`; shorter use `// inline`.
- File headers: name, short description, included files, files it is
  included in, dated changelog (most recent on top).

## Functional Requirements
- Code must work correctly and handle edge cases.
- Proper input validation and error handling; handle unexpected inputs
  gracefully.

---

# Error Handling

- Never show raw PHP errors/warnings to end users.
- Functions return predictable types on failure (empty array, false, null).
- External connections wrapped in try/catch — never let an external service
  failure crash the page.
- Always return valid JSON from AJAX endpoints with a success/error
  indicator.

---

# Debug Code — Remove Before Submitting

Search for and remove:
- `console.log(`
- `var_dump(`
- `print_r(`
- `if(true)` / `if (true)`
- `1==1`

For reliable local debug output prefer
`file_put_contents('/tmp/debug.log', ..., FILE_APPEND)` over on-page dumps.

---

# Development & Review Practices

- **Merge-base diff for reviews**: use `git diff <merge-base>..HEAD`, never
  tip-to-tip — it misreports target-only code as changes under review. Only
  flag issues introduced by the code under review.

## Mechanical Safe-Wrapper Audit (run after trace-based analysis)
After reasoning about the code, do a line-by-line check of all
changed/new code:

| Find | Must be | Native OK only if |
|------|---------|-------------------|
| `explode($delim, $var)` | `safe_explode(...)` | `$var` is a hardcoded string literal |
| `in_array($val, $arr)` | `safe_in_array(...)` | `$arr` is a hardcoded array literal |
| `implode($sep, $arr)` | `safe_implode(...)` | `$arr` is a hardcoded array literal |
| `count($var)` | `safe_count(...)` | `$var` is a hardcoded array literal |
| `array_filter($arr)` | `safe_array_filter(...)` | `$arr` is a hardcoded array literal |

For every `$_POST`/`$_GET` value expected to be an array, `isset()` alone is
NOT sufficient — it must also have an `is_array()` check:
`isset($_POST['k']) && is_array($_POST['k']) ? $_POST['k'] : []`.

---

# Issue Categories (Code Review)

| Severity | Examples |
|---|---|
| **Critical** | SQL injection, security vulnerabilities, fatal errors, data corruption |
| **Major** | Deprecated functions, logic flaws, missing validation, PHP compatibility, `??` operator |
| **Minor** | Performance, code quality, maintainability |

**Never flag:** Missing trailing newlines, mixed line endings,
whitespace/formatting inconsistencies.

**Only flag issues INTRODUCED by the code being reviewed.**

## Standards Enforcement Scope
- These standards apply ONLY to **new code** being added. Minor changes to
  existing lines do not require rewriting surrounding code to comply.
- Coding and styling standard violations are **NEVER Critical** (unless they
  independently cause a fatal error or security vulnerability):
  - **Major**: when the violation causes a functional problem, breaks theme
    compatibility, or creates a maintenance burden.
  - **Minor**: when the violation is cosmetic or a best-practice preference
    that doesn't affect functionality.
