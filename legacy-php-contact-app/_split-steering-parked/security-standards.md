---
inclusion: auto
name: security-standards
description: Security review standards for PHP code — SQL injection prevention, input validation/sanitization, authentication and authorization checks, file uploads. Use when reviewing PHP code for security vulnerabilities.
---

# Security Standards

## Input Validation
- Validate all user input — type checking, whitelist validation, length
  limits.
- Sources needing sanitization: `$_POST`, `$_GET`, `$_REQUEST`, `$_FILES`.
- Sources NOT needing sanitization: DB query results, `get_config()`,
  `get_contact()`, session values.
- Always use `isset()` before accessing `$_POST` / `$_GET` keys.
- Numbers: `intval($val)` or `(int)` cast.
- Numeric IDs: Always use `FILTER_SANITIZE_NUMBER_INT` (never
  `FILTER_SANITIZE_FULL_SPECIAL_CHARS` on numeric fields).
- Strings: `sanitize_input($val, FILTER_SANITIZE_FULL_SPECIAL_CHARS)`.
- Dates: `date('Y-m-d', strtotime($val))`.
- **Dates that drive automated actions** (auto-archive, auto-email, status
  transitions, expiry checks): `strtotime()` returns `false` on invalid
  input, which makes `date()` produce `'1970-01-01'` — a past date that
  immediately fires the action. Always check the result before storing:
  `$ts = strtotime($val); $date = ($ts !== false) ? date('Y-m-d', $ts) : null;`
- An `(int)` / `intval()` cast on a numeric user input IS acceptable
  sanitization — do not require it be replaced with a filter.

## File Upload Security
- Use `file_safe_str($filename, $folder)` for uploaded file names — it
  strips unsafe characters AND appends a numeric suffix if the file already
  exists in the target folder. This is the authoritative function;
  `unique_filename()` does not exist.
- Store uploads in the `download/` directory.
- Validate file size against expected limits.
- Use `move_uploaded_file()` — never copy/rename directly from tmp.
- Check `$_FILES['field']['error']` before processing.
- **Never trust the client-supplied MIME type or filename** — validate the
  extension against an allow-list and, where it matters, verify actual file
  contents; the browser-reported type is user-controlled.

## Output Escaping
- HTML context: `htmlspecialchars()`.
- URL context: `urlencode()`.
- JavaScript context: proper escaping.
- SQL context: prepared statements or `real_escape_string()`.
- **XSS analysis is skipped in QA reviews** — output escaping is handled at
  render time per the established codebase approach.

## Authentication & Authorization
- Always verify user permissions before operations.
- `checkAuthorised()` immediately after `include_once('../include.php')` on
  every endpoint.
- **`$guest_access = true` is a full authentication bypass.** It is correct
  only for genuinely public pages (public forms, cronjobs, featured
  galleries). It must NEVER appear on a configuration, admin, or settings
  page.
- **Slider / iframe includes are the established exception:** files loaded
  via `overlayIFrameSlider` do NOT call `checkAuthorised()` directly — they
  rely on the parent page having already authenticated the user. Do not
  flag a missing `checkAuthorised()` in slider/iframe includes during QA.
- Never rely on UI hiding alone for security.
- Field-level encryption via `encryptIt()` / `decryptIt()` for sensitive
  data.

## Session Context
- `$_SESSION['contactid']` — logged-in user's ID.
- `$_SESSION['main_contactid']` — real user when impersonating.
- Session cookie lifetime is 518400 seconds — do not shorten it in new code.

---

# Database & SQL Standards

## MySQL Style
- Keywords (`SELECT`, `WHERE`, etc.) uppercase.
- Table and column names in backticks.
- No spaces around operators in conditionals.
- Dates/datetimes stored only as `Y-m-d` or `Y-m-d H:i:s`.
- Queries should use OO mysqli (`$dbc->query()`).

## SQL Injection Prevention
- **Prepared statements preferred** for user input.
- **Non-prepared acceptable** when ALL variables are sanitized:
  - `FILTER_SANITIZE_NUMBER_INT` for numeric values
  - `(int)` or `(float)` type casting for numbers
  - `mysqli_real_escape_string()` for string values
  - `sanitize_input()` for string sanitization
- **Database-sourced values are safe from a sanitization standpoint** — no
  re-sanitization needed. HOWEVER, a DB-sourced string concatenated into a
  query STILL needs `real_escape_string()` for SQL *syntax* safety.
- **Never** concatenate unsanitized `$_GET`, `$_POST`, `$_REQUEST` directly
  into SQL.
- **Only flag SQL injection** when user input is directly concatenated with
  zero sanitization.
- **SQL identifiers** (column/table names): validate against a hardcoded
  whitelist array before use:
  ```php
  $allowed_columns = ['first_name', 'last_name', 'email_address'];
  if (in_array($field_name, $allowed_columns)) {
      $dbc->query("UPDATE `contacts` SET `$field_name`='$field_value' WHERE ...");
  }
  ```

## Soft Delete Values
| Value | Meaning |
|---|---|
| 0 | Active |
| 1 | Deleted / Archived |
| 2 | Hard Archived |
| 8 | Disabled |
| 9 | Estimates (preferred for new code) |

Rows should never be removed with `DELETE FROM` — use soft deletes, unless
the sample app's scope explicitly calls for a hard delete on a toy table
with no history requirement (note any deviation in review comments).

## Escape ALL Variables in SQL Helper Functions
Functions that build SQL queries must defensively escape all interpolated
variables — even when current callers pass sanitized values. The function
boundary is the safety boundary:
```php
function get_unique_username($dbc, $base_username, $contactid) {
    $safe_user = mysqli_real_escape_string($dbc, $base_username);
    $safe_id = mysqli_real_escape_string($dbc, $contactid);
    $result = $dbc->query("SELECT ... WHERE `user_name`='$safe_user' AND `contactid` != '$safe_id'");
}
```

---

## Issue Severity (for security findings)

| Severity | Examples |
|---|---|
| **Critical** | SQL injection, security vulnerabilities, fatal errors, data corruption |
| **Major** | Deprecated functions, missing validation, PHP compatibility |
| **Minor** | Performance, maintainability |

**Only flag issues INTRODUCED by the code under review.**
