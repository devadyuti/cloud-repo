---
inclusion: manual
---
# PHP Standards — Server-Side Logic, SQL and Database

Load when the work involves PHP logic, PHP 5.6/8.5 compatibility, null safety, queries, schema changes or server-side performance. Universal rules are in `essentials.md`. Input validation, SQL injection and authorization rules are in `security-standards.md`.

---

## PHP Compatibility Requirements

### Dual Version Support
- **MANDATORY**: All code MUST work on BOTH PHP 5.6 AND PHP 8.5
- **Null Coalescing (`??`)**: Does NOT exist in PHP 5.6 — causes fatal parse error. Use `isset($var) ? $var : $default`
- **Nullsafe Operator (`?->`)**: PHP 8.0+ only — do not use
- **Deprecated Functions**: Do not use functions removed/deprecated in PHP 8+ (e.g., `each()`, `create_function()`, `FILTER_SANITIZE_STRING`)
- **Type Declarations**: Avoid strict type declarations that break PHP 5.6
- **Spread Operator**: `...` in function declarations does not exist in PHP 5.6
- **`::class` on objects**: Not available in PHP 5.6
- **Language when flagging**: Only reference "PHP 5.6" and "PHP 8.5" — never intermediate versions. Never use "notice" or "warning" terminology for version differences — say "will not work on PHP X" or "fatal error on PHP X". (Exception: an undefined variable/array index is described as an "error on PHP 8.5".)

### Polyfilled Functions (Safe to Use)
These are polyfilled in the codebase and safe on PHP 5.6:
- `str_contains($string, 'needle')`
- `str_starts_with($string, 'prefix')`
- `str_ends_with($string, 'suffix')`
- `each()` — polyfilled but do NOT use in new code; use `foreach` instead

### Removed / Fatal on PHP 8.5 (Never Use in New Code)
These cause a fatal error on PHP 8.5 and must never appear in new code:
- `mysql_*` functions (removed) — use mysqli (`$dbc->query()`)
- `ereg()`, `eregi()`, `split()`, `spliti()` (removed) — use `preg_*` / `explode()`
- `create_function()` (removed) — use an anonymous function
- `get_magic_quotes_gpc()` / `get_magic_quotes_runtime()` (removed)
- `$HTTP_RAW_POST_DATA` (removed) — use `file_get_contents('php://input')`
- Curly-brace string/array access `$str{0}` (removed) — use `$str[0]`
- Unparenthesized nested ternary (fatal error on PHP 8.5) — always parenthesize: `$a ? $b : ($c ? $d : $e)`

### Cast / Function Modernization (Deprecated Forms)
- Use `(int)`, `(bool)`, `(float)` — not `(integer)`, `(boolean)`, `(double)`, `(real)`
- Use `mysqli_stmt_execute()` — not `mysqli_execute()`
- `imagedestroy()` / `curl_close()` are now no-ops — safe to leave or remove, do not rely on them freeing resources
- Other now-no-op resource-close functions (safe to remove in new code, GC handles them): `curl_share_close()`, `finfo_close()`, `xml_parser_free()`

### Behavioral Changes to Guard Against
- Loose comparison changed between versions (`0 == "foo"` is `false` on PHP 8.5) — prefer strict `===` when comparing mixed types. The `!=` counterpart is equally dangerous: `0 != 'tile_settings'` is **FALSE** on older versions (the string coerces to `0`), so use strict `!==` for any comparison where one side could be an integer `0` and the other a non-numeric string
- Accessing an undefined variable or array key is an error on PHP 8.5 — always `isset()` / initialize before use

### Deprecated / Removed Filter Constants
`FILTER_SANITIZE_STRING` and `FILTER_SANITIZE_STRIPPED` were deprecated in PHP 8.1 and removed in PHP 8.2. They are polyfilled but should not be used in new code:
```php
// Avoid in new code
sanitize_input($val, FILTER_SANITIZE_STRING);

// Use instead
sanitize_input($val, FILTER_SANITIZE_FULL_SPECIAL_CHARS); // HTML-safe strings
sanitize_input($val, FILTER_SANITIZE_NUMBER_INT);          // integers
```
Both `FILTER_SANITIZE_STRING` and `FILTER_SANITIZE_FULL_SPECIAL_CHARS` are acceptable when passed through `sanitize_input()` (it handles the deprecated flags).

### PHP 8.5 Null Safety
Many native functions that previously accepted `null` now throw fatal errors in PHP 8.5. Use safe wrapper functions from `php8_compatibility_fixes.php` when input could be `null`:

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
- Variable comes from DB query, `$_GET`, `$_POST`, function return, or any nullable source → use safe function
- Hardcoded literal (e.g., `explode(',', 'a,b,c')`) → native function is fine
- Already validated with `isset()` or type-checked immediately before → native function is acceptable

**Common null-fatal scenarios:**
- `explode(',', $nullable_var)` → `safe_explode(',', $nullable_var)`
- `count($nullable_var)` → `safe_count($nullable_var)`
- `in_array($val, $nullable_var)` → `safe_in_array($val, $nullable_var)`
- `strlen($nullable_var)` → `strlen(safe_string($nullable_var))`
- `trim($nullable_var)` → `trim(safe_string($nullable_var))`
- `strtolower($nullable_var)` / `strtoupper($nullable_var)` → wrap with `safe_string()`
- `strpos($nullable_var, ...)` → guard with `is_string()` or `isset()`
- `substr($nullable_var, ...)` / `str_replace(..., $nullable_var)` → guard with `is_string()` or `isset()`

**Additional PHP 8.5 checks:**
- **Destructuring non-arrays:** Using `list()` or `[]` destructuring on non-array values fails — ensure the value is an array first
- **Float-to-int cast:** Casting floats that cannot be represented as int is unreliable — only `(int)`/`intval()` values known to be representable
- **Function return values:** When a function may return `null` (array lookups, cache misses), guard with `isset($var) && isset($var['key'])`, not just `isset($var['key'])`

**Always use safe wrappers — no inline null guards:**
```php
// Wrong
in_array($val, is_array($arr) ? $arr : [])

// Correct
safe_in_array($val, $arr)
```

**Never remove the `php8_compatibility_fixes.php` include** from `shared_functions.php` — the standalone geo-location app depends on it being loaded there; removing it fatals the mobile API.

**`load_config()` return value:** `load_config()` does NOT return `null` — its final fallback is `''` (empty string) when no config row exists and no hardcoded default matches. Do not add null-guards around `load_config()`; use `empty()` checks where needed. Note `get_config()` likewise returns an empty string (not null/false) when a key is unset — a `?:` fallback won't trigger; use `if(empty(...))`.

**`get_field_value()` returns `null` on miss — unlike `get_config()`/`load_config()`:** `get_field_value($dbc, $field, $table, $key_column, $id)` returns `null` when the id is `0`/empty or no row matches. A very common pattern escapes its result straight into SQL, which fatals on PHP 8.5 because `mysqli_real_escape_string($dbc, null)` is a fatal error:
```php
// Wrong — get_field_value() returns null when $warehouseid is 0/empty
mysqli_real_escape_string($dbc, get_field_value('region', 'contacts', 'contactid', $warehouseid))
// Correct — wrap with safe_string() so a missing lookup becomes ''
mysqli_real_escape_string($dbc, safe_string(get_field_value('region', 'contacts', 'contactid', $warehouseid)))
```
Any place that resolves a value with `get_field_value()` and immediately passes it to a string function (`mysqli_real_escape_string()`, `trim()`, `strtolower()`, `explode()`, etc.) must guard for null — `safe_string()` is the simplest wrapper. Remember the distinction: `get_config()`/`load_config()` → `''` (no null guard needed); `get_field_value()` → `null` on miss (must be null-guarded before string use).

**`get_field_value()` return type depends on how many fields you request:** a single field name returns a **scalar string** (or `null` on miss); a comma-separated list of field names returns an **associative array** keyed by field name (or `null` on miss). Internally it returns the scalar when the fetched row has exactly one element, otherwise the whole row. The common trap is calling the single-field form and then testing `is_array()` — that is always `false`, so the value silently becomes empty:
```php
// Wrong — is_array() is always false for a single-field call, so $name is always ''
$lookup = get_field_value('product_name', 'inventory', 'inventoryid', $id, $dbc);
$name   = is_array($lookup) ? $lookup['product_name'] : '';
// Correct — single field returns a scalar
$name = safe_string(get_field_value('product_name', 'inventory', 'inventoryid', $id, $dbc));
// Multi-field — access by key
$fields  = get_field_value('part_no, code, product_name', 'inventory', 'inventoryid', $id, $dbc);
$part_no = is_array($fields) ? $fields['part_no'] : '';
```

**`fgetcsv()` cells can be null:** the same "null into a string function" fatal appears when parsing uploaded CSVs. `fgetcsv()` can yield `null` elements, so `array_map('trim', $headers)` / `array_map('strtolower', $headers)` fatal on PHP 8.5. Wrap each element: `array_map(function($v){ return trim(safe_string($v)); }, $headers)`.

---

## Performance
- Database queries should be efficient with proper indexing
- Avoid N+1 queries — batch fetch related data into lookup arrays before loops
- **N+1 scope — unbounded vs bounded contexts**: the rule targets *unbounded* loops where the iteration count scales with data volume (dashboard lists of 50–500+ rows, report `row_function()` callbacks, calendar month renders, export loops). It does NOT apply to *bounded* detail views where the row count is inherently single-digit AND the per-row lookup matches the pattern already used in that file and its companion/reload file — site visits per sales lead, pieces per ticket stop, staff per schedule stop, communication records in a slider. Refactoring those introduces risk to stable code for no measurable gain; do not flag them
- Avoid per-row queries in loops and report row functions — batch-fetch first, then read from array
- Pre-check before expensive UPDATEs — run a cheap `SELECT ... LIMIT 1` first and skip the UPDATE when nothing needs to change
- Avoid memory leaks; properly close connections and free resources
- Use appropriate caching (session, configuration, request-level)
- **`load_config()` loads ALL `general_configuration` rows into `$_SERVER['config']` on first call** — subsequent `get_config()` calls are in-memory lookups, NOT database queries. Repeated `get_config()` (or wrappers like `get_time_off_types()`) inside loops are NOT N+1 issues and must not be flagged as such
- In a per-row loop that also writes to a cache, defer the cache write until after the loop (or use a `defer_cache_write` flag) so a slow write is not repeated every iteration

## Query Performance Rules
- **Sargable date filters** — never wrap an indexed column in a function. Use `column BETWEEN 'YYYY-MM-DD 00:00:00' AND 'YYYY-MM-DD 23:59:59'` rather than `DATE(column) BETWEEN ...`
- **`IFNULL(col,0)=0` prevents index use** — use `(col = 0 OR col IS NULL)` instead
- **`OR` in a JOIN prevents index use** — split into two SELECTs joined by `UNION`
- **Comma-separated ID columns** — query with `FIND_IN_SET()`. Never assume `TRIM + IN` works
- **Match indexed columns exactly** — use `src_table='equipment'` (equality, uses the index), not `src_table LIKE 'equipment%'`
- **Replace a correlated `HAVING ... IN (SELECT ...)`** with a pre-fetched PHP `IN (list)` when the inner set is small and stable — avoids re-running the subquery per outer row
- **`ON DUPLICATE KEY UPDATE` (upserts)** — the UNIQUE index that detects the conflict must contain ONLY the lookup columns, never the column whose value you intend to change. E.g. to upsert `categoryid` keyed on `(item_code, chart_type)`, the UNIQUE key must be `(item_code, chart_type)` only; including `categoryid` in the unique key prevents conflict detection and inserts duplicates instead of updating

---

## Time & Date Display Standards

Every user-facing time MUST respect the customer's configured 12h/24h preference. Never output a raw `H:i:s` value straight from the database. This applies to every surface: card timestamps, tooltips, history rows, sidebar fields, slider content, report cells, PDF output.

- Preference source: `system_time_format` config (Settings → Display Preferences), with a per-user override in `$_SESSION['user_preferences']['time_format']`
- Standard wrapper: **`time_user_format($time, $seconds = false, $option = 'user')`** (`function.php`). Lower-level engine: `load_time_user_format($dbc, $details)` (`shared_functions.php`)
- Bootstrap constants: `TIME_FORMAT_PHP` (PHP `date()` string, e.g. `'h:i A'`), `TIME_FORMAT` (`'hh:mm tt'`), `TIME_FORMAT_SEC` (with seconds)
- JavaScript has no access to the helper — format on the server and return the formatted string in the AJAX response rather than formatting client-side

```php
// Correct — respects the user's preference (raw $row['created_date'] would force 24-hour)
$display_time = date('Y-m-d', strtotime($row['created_date'])).' '.time_user_format($row['created_date']);
```

---

## Database & SQL Standards

### MySQL Style
- Keywords (`SELECT`, `WHERE`, etc.) uppercase
- Table and column names in backticks
- No spaces around operators in conditionals
- Line breaks within a query only before `UNION`
- Dates/datetimes stored only as `Y-m-d` or `Y-m-d H:i:s`
- Queries should use OO mysqli (`$dbc->query()`)

SQL injection prevention, identifier whitelisting and input sanitization: see `security-standards.md`.

---

### Soft Delete Values
| Value | Meaning |
|---|---|
| 0 | Active |
| 1 | Deleted / Archived |
| 2 | Hard Archived |
| 3 | Recurring (legacy estimates may also use 3) |
| 4 | Pending Completion |
| 8 | Disabled |
| 9 | Estimates (preferred for new code) |

Follow existing usage in the file/feature. New code with no precedent uses `deleted=9` for estimates. This is a guideline — not a blocker for approval. Rows should never be removed with `DELETE FROM` — use soft deletes. New records that are inserted in a placeholder state (a blank new contact, an unopened editor row) are written with a non-active `deleted` value until a detail is entered — follow the existing flag value used by that feature; these transient rows are by design, not data loss.

### Database Structure Changes
All schema changes must be made via code in `db_structure/`:
- `db_tables.php` — CREATE TABLE statements (fresh-install schema)
- `db_fields.php` — ALTER TABLE for new/changed columns (existing DB migration)
- `db_indexes.php` — indexes
- `db_triggers.php` — triggers
- `db_defaults.php` — one-time or recurring data updates

**A new column MUST be added in BOTH `db_tables.php` AND `db_fields.php`** with identical definitions. If you change a column type, update `db_tables.php` and add the change in `db_fields.php`.

**Runtime column-ensure guards:** Some hot tables also have a runtime `ensure_*_columns()` check in `function.php` (e.g. `ensure_inv_bom_columns()`) that adds missing columns before that table's queries run. When adding a column to such a table, update ALL THREE locations (`db_tables.php`, `db_fields.php`, and the runtime ensure function) — missing any one causes failures on databases where the table exists but lacks the column.

**`db_update.php` load order — `db_fields.php` runs BEFORE `function.php`:** Code in `db_fields.php` that calls application functions (`get_config()`, `get_field_value()`, etc.) causes a fatal error that halts ALL schema updates for every customer, because those functions are not yet loaded. Any migration logic that needs application functions belongs in `db_defaults.php` (which runs after `function.php`).

**`db_defaults.php` run-once mechanism:** one-time data updates are guarded by a key added to the `general_configuration.db_update_data` CSV via the `$config_complete` list — a block runs only if its key is not already present, then appends its key. Ordering matters: a block that depends on an earlier block's data must appear after it.

**Disabling a migration block for per-customer enablement:** when a `db_defaults.php` block should NOT auto-run on all customers at deploy (e.g. scope field defaults that vary per customer), prefix the guard with `false &&` to keep the block in place while disabling it. Enable it for a specific customer by removing `false &&`, running `db_update.php`, then restoring `false &&` for others. Document which blocks are disabled and why in the QA notes Configuration section so the push-live team knows which to enable per customer:
```php
if(false && !safe_in_array('db_update_scope_field_defaults_v2', $config_complete)) {
    // migration logic here
    $config_complete[] = 'db_update_scope_field_defaults_v2';
}
```

**Never run `CREATE INDEX` directly** — always add to `db_indexes.php`:
```php
if (!isset($db_indices['table']['index_name']) && !mysqli_query($dbc, "CREATE INDEX ...")) {
    echo "Error: ".mysqli_error($dbc)."<br />\n";
}
```

Use transactions for multi-step operations. Stored procedures/triggers are ideal but not a rejection reason for code that doesn't use them. Transaction-less multi-write code that already exists is acceptable and should not be flagged as a blocker.

### One-Time / Per-Customer Scripts (outside `db_structure/`)

A standalone PHP, SQL or JS script that applies a configuration change, data migration or one-time fix for a **specific customer** (i.e. NOT a `db_defaults.php` block that runs for every customer on deploy) MUST live in the `/tmp/` folder at the project root — `/tmp/{descriptive_name}.php`.

- **Database guard**: include a runtime check that aborts if the connected database is not the intended target, so the script cannot run against the wrong customer
- **Idempotent**: safe to re-run without creating duplicates or overwriting intentional changes
- **Delete after use**: run once, verify the output, then delete. Never commit it to the repository
- **Applies to** any direct PHP script, raw SQL file or JS script that writes configuration/data outside the `db_structure/` migration system. If a ticket says "run this on environment X" or "one-time config change for customer Y", it goes in `/tmp/`

### db_defaults.php Migration Scoping
- A migration that enables a **child field config** which depends on a parent feature MUST scope its `UPDATE` to only the URLs/customers where the parent is already configured. Without a parent check, every customer gets the new field enabled on deploy and it appears on configurations that never opted into the parent feature:
  ```php
  // Wrong — enables for ALL customers regardless of parent
  $dbc->query("UPDATE `field_config` SET `tickets`=CONCAT(`tickets`,',Child Field')
      WHERE `deleted`=0 AND `tickets` NOT LIKE '%Child Field%'");

  // Correct — only where the parent field is already configured
  $dbc->query("UPDATE `field_config` SET `tickets`=CONCAT(`tickets`,',Child Field')
      WHERE `deleted`=0 AND `tickets` LIKE '%Parent Field%' AND `tickets` NOT LIKE '%Child Field%'");
  ```
- **Remediating a bad migration that already ran:** you cannot fix the original block — it already executed and won't re-run (guarded by `$config_complete`). Add a SEPARATE remediation block with its own guard key:
  ```php
  if(!in_array('child_field_fix', $config_complete)) {
      $dbc->query("UPDATE `field_config` SET `tickets`=REPLACE(`tickets`,',Child Field','')
          WHERE `deleted`=0 AND `tickets` LIKE '%Child Field%'
          AND NOT EXISTS (SELECT 1 FROM `field_config_ticket_fields`
              WHERE `deleted`=0 AND `accordion`='Section' AND `fields` LIKE '%Parent Field%')");
      $config_complete[] = 'child_field_fix';
  }
  ```

### Database Design Principles
- Each column should hold only one value (no CSV, no JSON except formatting data like Forms)
- Normalized structure allowing full range of user options
- History table for changes to user data and settings, tied to primary key and username (initially inserted by triggers, updated by PHP)
- Pivot tables for many-to-many relationships
- Every table must have a numeric unsigned int primary key
- Tables should have a TINYINT `deleted` and DATETIME `date_of_archival` column

### RDS AUTO_INCREMENT Reads Stale
After `ALTER TABLE ... AUTO_INCREMENT = N` on RDS, `information_schema.TABLES.AUTO_INCREMENT` may show the old value; run `ANALYZE TABLE tablename` to refresh the metadata (the actual auto_increment is applied correctly regardless).

### CLI Database Selection Trap
`db_connect.php` selects the database differently under CLI vs web — when running a script from the command line, confirm the intended customer DB is actually selected before trusting query results.

---

## Defensive Coding Patterns

### Query Result Safety
Never chain `->fetch_assoc()` on `$dbc->query()` — always store result first:
```php
$result = $dbc->query("SELECT ...");
$row = $result ? $result->fetch_assoc() : null;
```
Never pass `mysqli_query()` directly to `mysqli_fetch_all()` / `mysqli_fetch_array()` / `mysqli_fetch_assoc()`:
```php
$result = mysqli_query($dbc, "SELECT ...");
$rows = $result ? mysqli_fetch_all($result, MYSQLI_ASSOC) : [];
```
When using `mysqli_fetch_all($result, MYSQLI_ASSOC)`, access columns by name, never by numeric index. Guard `while($row = $result->fetch_assoc())` loops with `if($result)` first (a `false` result fatals on PHP 8.5).

### Variable Initialization
Always initialize variables with defaults before conditional blocks:
```php
$filter = '';
if ($condition) { $filter = "AND status='Active'"; }
```

### Never Iterate / Pass Null
Never iterate over or pass a potentially-null variable to string/array functions (`decryptIt()`, `str_replace()`, `ucwords()`, `explode()`, `strlen()`, `foreach`):
```php
$fields = isset($_POST['fields']) && is_array($_POST['fields']) ? $_POST['fields'] : [];
$value  = !empty($row['value']) ? decryptIt($row['value']) : '';
```

### Comma-Wrapped Config empty() Trap
A comma-wrapped config value used for `strpos` matching is NEVER empty — `','.get_config($dbc,'key').','` is `',,'` even when the key is unset. Always test the RAW value with `empty()` BEFORE wrapping:
```php
$raw = get_config($dbc, 'key');
if (empty($raw)) { /* treat as unset */ }
$wrapped = ','.$raw.','; // only for FIND-style strpos matching
```

### $options / Optional-Key Guards
When a function receives an `$options`/config array, guard each optional key with `isset()` before reading it — do not assume the caller populated it. Use `!empty()` when an optional array key both may be missing and may be empty.

### Guard glob() Return Value
`glob()` returns `false` on error. Never use `foreach(glob(...) as ...)` directly:
```php
$result = glob($path.'*.pdf', GLOB_BRACE);
if(is_array($result)) {
    foreach($result as $file) { ... }
}
```

### isset() on Nested Array Keys
```php
if (isset($arr[$key]['type']) && $arr[$key]['type'] == 'dropdown') { ... }
```

### Explode Index Safety
`explode()`/`safe_explode()` may return fewer parts than expected when the delimiter is absent — always check the index exists before reading it:
```php
$parts = safe_explode('_value_', $conditions);
if (isset($parts[0]) && isset($parts[1])) {
    $match_value = $parts[1];
}
```

### array_shift() By-Reference
Never pass a function return directly to `array_shift()`:
```php
$cats = array_filter(safe_explode(',', get_config($dbc, 'key')));
$label = array_shift($cats);
```

### Config Key Renames — Backward Compatibility
```php
$value = get_config($dbc, 'new_key_name');
if (empty($value)) { $value = get_config($dbc, 'old_key_name'); }
```
The config **key** (DB value, e.g. `general_configuration.name`) must never change — it breaks all existing customers. The **label** (display text) can be updated.

### is_array() Before Array Functions on User Input
Always check `is_array()` before passing `$_POST`/`$_GET` values to `array_map`, `array_filter`, `implode`, etc.

### ob_clean() Rules
- Only use in files that are exclusively AJAX endpoints
- Never use in files also included via PHP `include()` — it strips styles and scripts from the parent
- **Dual-use files (included during render AND called directly via AJAX) must gate on the request header, not just a `$_GET` flag** — if the URL parameter reaches the file through a normal browser request (bookmark, history, copy-paste), `ob_clean()` wipes the whole buffer and strips the head, CSS, navigation and everything rendered before the include point. Add the `XMLHttpRequest` check: `if(isset($_GET['ajax_load']) && $_GET['ajax_load'] == 1 && isset($_SERVER['HTTP_X_REQUESTED_WITH']) && $_SERVER['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest') { ob_clean(); }`. jQuery `.load()`, `$.get()` and `$.ajax()` always send that header, so legitimate AJAX callers still pass
- When you need an include ONLY for the variables it sets (but it also echoes HTML you want to discard), wrap the include: `ob_start(); include('...'); ob_end_clean();` — this keeps the variables in scope while dropping the HTML. Do NOT use `ob_clean()` for this (it does not close the buffer) and do NOT skip buffering (the unwanted HTML leaks into the page)

### HTML Content Saving
- Never use `FILTER_SANITIZE_FULL_SPECIAL_CHARS` on TinyMCE/HTML content — it destroys tags
- Use `safe_string()` before `encryptIt()`, let `real_escape_string()` handle SQL safety
- Strip literal `\r\n` from TinyMCE HTML before storing:
  ```php
  $value = encryptIt(str_replace(["\r\n", "\r", "\n"], ' ', safe_string($_POST['html_content'])));
  ```

### Fractional Numeric Input
When user input allows decimals (e.g., hours with `step="0.5"`), never use `(int)` in calculations — it silently truncates. Convert to a smaller whole unit:
```php
// Wrong — 1.5 hours becomes 1 hour
$end_time = date('H:i', strtotime($start . ' + ' . (int)$hours . ' hours'));
// Correct — 1.5 hours becomes 90 minutes
$end_time = date('H:i', strtotime($start . ' + ' . (int)($hours * 60) . ' minutes'));
```

### Pre-fetch Query Guards
Queries only used inside a conditional branch MUST be inside that branch:
```php
if ($some_condition && !empty($ids)) {
    $result = $dbc->query("SELECT ... WHERE contactid IN ($ids)");
}
```

### Static Cache — array_key_exists() Not isset()
Use `array_key_exists($key, $cache)` instead of `isset($cache[$key])` — `isset()` returns `false` when the stored value is `null`, causing re-queries:
```php
static $cache = [];
if (array_key_exists($id, $cache)) { return $cache[$id]; }
```

### Cache Format Must Match Fallback
When batch pre-fetching into a cache array, the function call used to populate the cache MUST be identical to the fallback call on a cache miss. Do not leave a dead/never-hit cache array behind from an incomplete optimization.

### isset() Guard Logic
When adding `isset()` checks, verify the "not set" case preserves original behavior:
```php
// Wrong — breaks default case (view not set = normal edit mode)
isset($_GET['view']) && $_GET['view'] !== 'readonly'
// Correct — preserves default truthy behavior
!isset($_GET['view']) || $_GET['view'] !== 'readonly'
```

### SQL Parenthesis Balance
When replacing subqueries with static lists, verify `(` and `)` counts match. Use `safe_implode()` for `IN (...)` lists from potentially empty/null arrays.

### field_config_contacts Queries
Always filter by `subtab='**no_subtab**'` and include `tile_name` when fetching the configured field list for a contact category. The `contacts` column stores label values, not field keys.

### Escape ALL Variables in SQL Helper Functions
Functions that build SQL queries must defensively escape all interpolated variables — even when current callers pass sanitized values. The function boundary is the safety boundary:
```php
function get_unique_username($dbc, $base_username, $contactid) {
    $safe_user = mysqli_real_escape_string($dbc, $base_username);
    $safe_id = mysqli_real_escape_string($dbc, $contactid);
    $result = $dbc->query("SELECT ... WHERE `user_name`='$safe_user' AND `contactid` != '$safe_id'");
}
```

### Form Field POST Key Format
Field names in `user_form_fields.name` are stored as `field_123`. The HTML POST key is `field_` + name = `field_field_123`. Contact picker SELECT fields submit as nested arrays keyed by `field_id`.

### Dead Code from Incomplete Refactors
When replacing legacy code with new dynamic code, the old lines MUST be removed. Two recurring patterns to flag:
1. **Query variable overwrite:** a new filtered query is assigned to `$query`, then the old unfiltered query immediately reassigns `$query` below — the new code is dead and the old behavior persists.
2. **Duplicate HTML elements:** a new `<td>` is added for dynamic content but the old hardcoded `<td>` is left in place — both render, breaking the table column count.

### $_SESSION Writes After session_write_close() Are Silently Lost
`global.php` calls `@session_write_close()` during the include chain (before most page/render code runs). Once the session is write-closed, `$_SESSION[...]` assignments still succeed **in memory** but are NEVER flushed to the session file. Any later request that reads the session from disk (e.g. a separate AJAX endpoint) finds nothing. Silent — no error, no warning. Any code that writes to `$_SESSION` during page render (or in a shared class/helper invoked at render time) and expects a **later, separate request** to read it back MUST reopen the session for the write:
```php
@session_start(['cookie_lifetime' => 518400]);
$_SESSION['key'] = $value;
@session_write_close();
```
Reading `$_SESSION` in the same request does not need this — only cross-request persistence requires the reopen. Known regression shape: a render-time helper wrote dynamic-Select2 SQL config to `$_SESSION`, and the AJAX dropdown endpoint read an empty session — every SQL-driven report dropdown returned no options until the reopen/write/close was added.

### String Accumulator / DB-Result Variable Collision
When building HTML/string output via `.=` into a variable inside a loop, never reuse that variable name for a DB fetch within the same scope. Overwriting a string accumulator with an array (a `mysqli_fetch_assoc()` result) causes a fatal "Unsupported operand types: array . string" on PHP 8.5. `error_reporting(0)` suppresses the on-screen error, so the symptom is silently empty output. Use a distinctly named variable for any mid-loop DB lookup result:
```php
// Wrong — overwrites the string accumulator, fatal on PHP 8.5
$warehouses = mysqli_fetch_assoc(mysqli_query($dbc, "SELECT ..."));
$warehouses .= '<li>...';
// Correct — separate name for the lookup result
$user_region_warehouse = mysqli_fetch_assoc(mysqli_query($dbc, "SELECT ..."));
$warehouses .= '<li>...';
```

### Division Guard
Every division where the divisor comes from a variable MUST be guarded against divide-by-zero:
```php
$safe_qty = $row['quantity'] > 0 ? $row['quantity'] : 1;
// Or in SQL:
SELECT IF(`quantity` > 0, `shipping_amount`/`quantity`, 0) ...
```

### HTML Regex Must Not Assume Fixed Attribute Ordering
When using `preg_replace_callback` or `preg_match` to find/modify HTML elements by class name, the regex must not assume the `class` attribute appears in a fixed position:
```php
// WRONG — fails when class is not the first attribute
'/<span\s+class="rc-checkbox"([^>]*)>/'
// CORRECT — matches class anywhere in the attribute list
'/<span\s+([^>]*class="[^"]*rc-checkbox[^"]*"[^>]*)>/'
```

### Split Multi-Table JOIN UPDATEs (Trigger Conflicts)
The four contact child tables (`contacts_cost`, `contacts_dates`, `contacts_description`, `contacts_medical`) each have AFTER UPDATE triggers that update `contacts.last_updated_time`. A single multi-table `JOIN UPDATE` touching `contacts` and its child tables together causes the triggers to update the parent `contacts` row simultaneously, producing conflicts. Split into per-table UPDATE statements:
```php
// Wrong — triggers conflict
$dbc->query("UPDATE contacts c JOIN contacts_cost cc ON c.contactid=cc.contactid SET c.field1='v', cc.field2='v' WHERE c.contactid=$id");
// Correct — separate statements
$dbc->query("UPDATE contacts SET field1='v' WHERE contactid=$id");
$dbc->query("UPDATE contacts_cost SET field2='v' WHERE contactid=$id");
```
This matters in `Staff/field_config_import.php` (CSV contact import) and any bulk update touching contacts + child tables in one query.

### Other Defensive Rules
- **Guard-pattern consistency within a file** — when a file already establishes a guard style for a given kind of value (e.g. `isset($x) ? $x : ''` or a `safe_*` wrapper), new code in that same file must use the SAME guard style. Mixing an unguarded access into a file that guards everywhere else is both a latent bug and a review flag
- Switch/case: verify `break;` and next `case` at same indentation level (misindented case becomes an unreachable label). A comment is required when intentionally omitting a `break`
- Conditional `<th>` must have matching conditional `<td>` with the exact same condition
- SELECT must include all fields accessed in all code paths
- Duplicated logic must match the original unless the difference is intentional and commented
- Never add `include_once('../include.php')` in files already included by a bootstrapped parent
- Never re-sanitize database-sourced values (causes double-encoding)
- JavaScript `.every()` on empty arrays returns `true` (vacuous truth) — guard with `arr.length > 0 &&` first
