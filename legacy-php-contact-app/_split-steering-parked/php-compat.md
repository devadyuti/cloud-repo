---
inclusion: auto
name: php-compat
description: Full PHP 5.6/8.5 compatibility rules and defensive coding patterns for null safety, deprecated/removed functions, and query result handling. Use when reviewing or writing PHP code for version compatibility or null-safety issues.
---

# PHP Compatibility Requirements (Full)

## Dual Version Support
- **MANDATORY**: All code MUST work on BOTH PHP 5.6 AND PHP 8.5.
- **Null Coalescing (`??`)**: Does NOT exist in PHP 5.6 — causes fatal parse
  error. Use `isset($var) ? $var : $default`.
- **Nullsafe Operator (`?->`)**: PHP 8.0+ only — do not use.
- **Deprecated Functions**: Do not use functions removed/deprecated in PHP 8+
  (e.g., `each()`, `create_function()`, `FILTER_SANITIZE_STRING`).
- **Type Declarations**: Avoid strict type declarations that break PHP 5.6.
- **Spread Operator**: `...` in function declarations does not exist in
  PHP 5.6.
- **`::class` on objects**: Not available in PHP 5.6.
- **Language when flagging**: Only reference "PHP 5.6" and "PHP 8.5" — never
  intermediate versions. Never use "notice" or "warning" terminology for
  version differences — say "will not work on PHP X" or "fatal error on
  PHP X". (Exception: an undefined variable/array index is described as an
  "error on PHP 8.5".)

## Polyfilled Functions (Safe to Use)
These are polyfilled in the codebase and safe on PHP 5.6:
- `str_contains($string, 'needle')`
- `str_starts_with($string, 'prefix')`
- `str_ends_with($string, 'suffix')`
- `each()` — polyfilled but do NOT use in new code; use `foreach` instead

## Removed / Fatal on PHP 8.5 (Never Use in New Code)
These cause a fatal error on PHP 8.5 and must never appear in new code:
- `mysql_*` functions (removed) — use mysqli (`$dbc->query()`)
- `ereg()`, `eregi()`, `split()`, `spliti()` (removed) — use `preg_*` /
  `explode()`
- `create_function()` (removed) — use an anonymous function
- `get_magic_quotes_gpc()` / `get_magic_quotes_runtime()` (removed)
- `$HTTP_RAW_POST_DATA` (removed) — use `file_get_contents('php://input')`
- Curly-brace string/array access `$str{0}` (removed) — use `$str[0]`
- Unparenthesized nested ternary (fatal error on PHP 8.5) — always
  parenthesize: `$a ? $b : ($c ? $d : $e)`

## Cast / Function Modernization (Deprecated Forms)
- Use `(int)`, `(bool)`, `(float)` — not `(integer)`, `(boolean)`, `(double)`,
  `(real)`
- Use `mysqli_stmt_execute()` — not `mysqli_execute()`
- `imagedestroy()` / `curl_close()` are now no-ops — safe to leave or remove,
  do not rely on them freeing resources
- Other now-no-op resource-close functions (safe to remove in new code, GC
  handles them): `curl_share_close()`, `finfo_close()`, `xml_parser_free()`

## Behavioral Changes to Guard Against
- Loose comparison changed between versions (`0 == "foo"` is `false` on
  PHP 8.5) — prefer strict `===` when comparing mixed types. The `!=`
  counterpart is equally dangerous: `0 != 'tile_settings'` is **FALSE** on
  older versions (the string coerces to `0`), so use strict `!==` for any
  comparison where one side could be an integer `0` and the other a
  non-numeric string.
- Accessing an undefined variable or array key is an error on PHP 8.5 —
  always `isset()` / initialize before use.

## Deprecated / Removed Filter Constants
`FILTER_SANITIZE_STRING` and `FILTER_SANITIZE_STRIPPED` were deprecated in
PHP 8.1 and removed in PHP 8.2. They are polyfilled but should not be used
in new code:
```php
// Avoid in new code
sanitize_input($val, FILTER_SANITIZE_STRING);

// Use instead
sanitize_input($val, FILTER_SANITIZE_FULL_SPECIAL_CHARS); // HTML-safe strings
sanitize_input($val, FILTER_SANITIZE_NUMBER_INT);          // integers
```
Both `FILTER_SANITIZE_STRING` and `FILTER_SANITIZE_FULL_SPECIAL_CHARS` are
acceptable when passed through `sanitize_input()` (it handles the deprecated
flags).

## PHP 8.5 Null Safety
Many native functions that previously accepted `null` now throw fatal errors
in PHP 8.5. Use safe wrapper functions from `php8_compatibility_fixes.php`
when input could be `null`:

| Use This | Instead Of | Behavior on null/invalid |
|---|---|---|
| `safe_explode($delimiter, $string)` | `explode()` | Returns `array()` |
| `safe_implode($separator, $array)` | `implode()` | Returns `''` |
| `safe_count($var)` | `count()` | Returns `0` |
| `safe_array($var)` | Array cast | Returns `array()` |
| `safe_string($var)` | String cast | Returns `''` |
| `safe_in_array($needle, $haystack)` | `in_array()` | Returns `false` |
| `safe_array_filter($array)` | `array_filter()` | Returns `array()` |
| `sanitize_input($variable, $flag)` | `filter_var()` with deprecated flags | Handles null and deprecated flags |

**When to use safe functions:**
- Variable comes from DB query, `$_GET`, `$_POST`, function return, or any
  nullable source → use safe function
- Hardcoded literal (e.g., `explode(',', 'a,b,c')`) → native function is fine
- Already validated with `isset()` or type-checked immediately before →
  native function is acceptable

**Common null-fatal scenarios:**
- `explode(',', $nullable_var)` → `safe_explode(',', $nullable_var)`
- `count($nullable_var)` → `safe_count($nullable_var)`
- `in_array($val, $nullable_var)` → `safe_in_array($val, $nullable_var)`
- `strlen($nullable_var)` → `strlen(safe_string($nullable_var))`
- `trim($nullable_var)` → `trim(safe_string($nullable_var))`
- `strtolower($nullable_var)` / `strtoupper($nullable_var)` → wrap with
  `safe_string()`
- `strpos($nullable_var, ...)` → guard with `is_string()` or `isset()`
- `substr($nullable_var, ...)` / `str_replace(..., $nullable_var)` → guard
  with `is_string()` or `isset()`

**Additional PHP 8.5 checks:**
- **Destructuring non-arrays:** Using `list()` or `[]` destructuring on
  non-array values fails — ensure the value is an array first
- **Float-to-int cast:** Casting floats that cannot be represented as int is
  unreliable — only `(int)`/`intval()` values known to be representable
- **Function return values:** When a function may return `null` (array
  lookups, cache misses), guard with `isset($var) && isset($var['key'])`,
  not just `isset($var['key'])`

**Always use safe wrappers — no inline null guards:**
```php
// Wrong
in_array($val, is_array($arr) ? $arr : [])

// Correct
safe_in_array($val, $arr)
```

**Never remove the `php8_compatibility_fixes.php` include** from
`shared_functions.php` — the standalone geo-location app depends on it being
loaded there; removing it fatals the mobile API.

---

# Defensive Coding Patterns

## Query Result Safety
Never chain `->fetch_assoc()` on `$dbc->query()` — always store result first:
```php
$result = $dbc->query("SELECT ...");
$row = $result ? $result->fetch_assoc() : null;
```
Never pass `mysqli_query()` directly to `mysqli_fetch_all()` /
`mysqli_fetch_array()` / `mysqli_fetch_assoc()`:
```php
$result = mysqli_query($dbc, "SELECT ...");
$rows = $result ? mysqli_fetch_all($result, MYSQLI_ASSOC) : [];
```
When using `mysqli_fetch_all($result, MYSQLI_ASSOC)`, access columns by
name, never by numeric index. Guard `while($row = $result->fetch_assoc())`
loops with `if($result)` first (a `false` result fatals on PHP 8.5).

## Variable Initialization
Always initialize variables with defaults before conditional blocks:
```php
$filter = '';
if ($condition) { $filter = "AND status='Active'"; }
```

## Never Iterate / Pass Null
Never iterate over or pass a potentially-null variable to string/array
functions (`decryptIt()`, `str_replace()`, `ucwords()`, `explode()`,
`strlen()`, `foreach`):
```php
$fields = isset($_POST['fields']) && is_array($_POST['fields']) ? $_POST['fields'] : [];
$value  = !empty($row['value']) ? decryptIt($row['value']) : '';
```

## Comma-Wrapped Config empty() Trap
A comma-wrapped config value used for `strpos` matching is NEVER empty —
`','.get_config($dbc,'key').','` is `',,'` even when the key is unset.
Always test the RAW value with `empty()` BEFORE wrapping:
```php
$raw = get_config($dbc, 'key');
if (empty($raw)) { /* treat as unset */ }
$wrapped = ','.$raw.','; // only for FIND-style strpos matching
```

## $options / Optional-Key Guards
When a function receives an `$options`/config array, guard each optional
key with `isset()` before reading it — do not assume the caller populated
it. Use `!empty()` when an optional array key both may be missing and may
be empty.

## Guard glob() Return Value
`glob()` returns `false` on error. Never use `foreach(glob(...) as ...)`
directly:
```php
$result = glob($path.'*.pdf', GLOB_BRACE);
if(is_array($result)) {
    foreach($result as $file) { ... }
}
```

## isset() on Nested Array Keys
```php
if (isset($arr[$key]['type']) && $arr[$key]['type'] == 'dropdown') { ... }
```

## Explode Index Safety
`explode()`/`safe_explode()` may return fewer parts than expected when the
delimiter is absent — always check the index exists before reading it:
```php
$parts = safe_explode('_value_', $conditions);
if (isset($parts[0]) && isset($parts[1])) {
    $match_value = $parts[1];
}
```

## array_shift() By-Reference
Never pass a function return directly to `array_shift()`:
```php
$cats = array_filter(safe_explode(',', get_config($dbc, 'key')));
$label = array_shift($cats);
```

## is_array() Before Array Functions on User Input
Always check `is_array()` before passing `$_POST`/`$_GET` values to
`array_map`, `array_filter`, `implode`, etc.

## Fractional Numeric Input
When user input allows decimals (e.g., hours with `step="0.5"`), never use
`(int)` in calculations — it silently truncates. Convert to a smaller whole
unit:
```php
// Wrong — 1.5 hours becomes 1 hour
$end_time = date('H:i', strtotime($start . ' + ' . (int)$hours . ' hours'));
// Correct — 1.5 hours becomes 90 minutes
$end_time = date('H:i', strtotime($start . ' + ' . (int)($hours * 60) . ' minutes'));
```

## Division Guard
Every division where the divisor comes from a variable MUST be guarded
against divide-by-zero:
```php
$safe_qty = $row['quantity'] > 0 ? $row['quantity'] : 1;
```

## Other Defensive Rules
- **Guard-pattern consistency within a file** — when a file already
  establishes a guard style for a given kind of value (e.g.
  `isset($x) ? $x : ''` or a `safe_*` wrapper), new code in that same file
  must use the SAME guard style. Mixing an unguarded access into a file that
  guards everywhere else is both a latent bug and a review flag.
- Switch/case: verify `break;` and next `case` at same indentation level
  (misindented case becomes an unreachable label). A comment is required
  when intentionally omitting a `break`.
- SELECT must include all fields accessed in all code paths.
- Never re-sanitize database-sourced values (causes double-encoding).
- JavaScript `.every()` on empty arrays returns `true` (vacuous truth) —
  guard with `arr.length > 0 &&` first.
