---
inclusion: manual
---
> **Superseded 2026-08-19.** This document has been split by topic so that only `essentials.md` loads on
> every interaction. Its content now lives in `essentials.md`, `php-standards.md`,
> `javascript-standards.md`, `html-css-standards.md`, `security-standards.md`, `qa-process.md`,
> `architecture-patterns.md` and `module-knowledge.md`. It is kept here (excluded from automatic
> loading) only as a reference copy while the split is validated — delete it once validation passes.

# ExampleApp Development Standards

**Version: 2026-08-11**
**Applies to: All Developers**

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

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Variables | snake_case (full words) | `$contact_name` |
| Functions (PHP) | snake_case (full words) | `get_contact_data()` |
| Functions (JS) | camelCase (short words) | `overlayIFrameSlider()` |
| Constants | UPPERCASE with underscores | `DATABASE_NAME` |
| Database tables | singular, lowercase + underscores | `contact_field` |
| Database fields | lowercase with underscores | `contact_fields` |
| File names | underscore-separated lowercase | `edit_tickets.php` |
| Tab-within-parent files | parent's name | `edit_<tab>.php`, `edit_<tile>.php`, `index.php` |
| JS functional selectors | underscore-separated classes | `_save_button` |
| CSS styling selectors | dash-separated classes | `save-button` |

- Column names cannot use MySQL keywords (`order`, `int`, `date`, `time`, `datetime`)
- HTML `id` attributes should not be used — reference elements by class, type, and relative position

---

## Code Quality Standards

### Clean Code
- Code should be self-documenting with clear variable and function names
- Never duplicate code — pass variables to a shared function or include a shared file
- Proper file structure and logical code organization
- Tabs for indentation (at the start of the line)
- Opening brace on same line (functions, if blocks)
- Single quotes for PHP strings; double quotes for MySQL queries
- One statement per line — never more than one
- One space after commas and control characters (closing parens, ampersands, semicolons); no double spaces; no trailing whitespace
- No space after open parens or before `{ } [ ] ( )` (unless immediately preceded by a control character)
- Maximum 1 blank line between blocks
- No mid-line alignment with spaces (do not align variable assignments into columns)
- Child sections indented from their parent (function body, loop, conditional, HTML divs)
- Files that are entirely PHP: no closing `?>`
- Keywords/system constants (`true`, `false`, `null`, `const`) lowercase; defined constants UPPERCASE
- Group `if / else` rather than subsequent independent `if` conditionals where possible
- PHP includes should use document root: `$_SERVER['DOCUMENT_ROOT'].'/include.php'`

### Inserting Code into Existing Files
When adding code to an existing file, trace the brace/branch nesting first — do not assume the first matching occurrence is the right place:
- Identify EVERY `if / else if / else` (or `switch case`) branch the new behavior must apply to, and add the code to ALL of them — a value set in only one branch silently misbehaves in the others
- Confirm the insertion point is inside the correct block by matching opening/closing braces, not by visual proximity
- When a variable is read later in multiple code paths, ensure it is assigned in every path that reaches that read

### Comments
- Comment at least each function (purpose + each parameter)
- Comment most conditional / switch / loop blocks, and non-obvious lines/variables
- Comments ≥ 3 lines use `/* block */`; shorter use `// inline`
- When commenting out code, note the date; remove commented code older than three months
- File headers: name, short description, included files, files it is included in, dated changelog (most recent on top)

### Functional Requirements
- Code must work correctly and handle edge cases
- Proper input validation and error handling; handle unexpected inputs gracefully
- Functions should accept an object/array with named elements so variables can be passed in any order

### Performance
- Database queries should be efficient with proper indexing
- Avoid N+1 queries — batch fetch related data into lookup arrays before loops
- **N+1 scope — unbounded vs bounded contexts**: the rule targets *unbounded* loops where the iteration count scales with data volume (dashboard lists of 50–500+ rows, report `row_function()` callbacks, calendar month renders, export loops). It does NOT apply to *bounded* detail views where the row count is inherently single-digit AND the per-row lookup matches the pattern already used in that file and its companion/reload file — site visits per sales lead, pieces per ticket stop, staff per schedule stop, communication records in a slider. Refactoring those introduces risk to stable code for no measurable gain; do not flag them
- Avoid per-row queries in loops and report row functions — batch-fetch first, then read from array
- Pre-check before expensive UPDATEs — run a cheap `SELECT ... LIMIT 1` first and skip the UPDATE when nothing needs to change
- Avoid memory leaks; properly close connections and free resources
- Use appropriate caching (session, configuration, request-level)
- **`load_config()` loads ALL `general_configuration` rows into `$_SERVER['config']` on first call** — subsequent `get_config()` calls are in-memory lookups, NOT database queries. Repeated `get_config()` (or wrappers like `get_time_off_types()`) inside loops are NOT N+1 issues and must not be flagged as such
- In a per-row loop that also writes to a cache, defer the cache write until after the loop (or use a `defer_cache_write` flag) so a slow write is not repeated every iteration

### Query Performance Rules
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

## ExampleApp Architecture Patterns

### Core Patterns
- Always include `include.php` as master bootstrap
- Use `$dbc` for database connection (OO style preferred)
- Use `get_config($dbc, 'name')` for configuration values
- Use `get_contact($dbc, $contactid, 'field')` for contact data
- Use `get_field_value($dbc, ...)` for field value lookups
- When pulling/storing data, prefer a reusable function over inline queries
- Soft deletes via `deleted` field (see values below)
- Permission checks: `checkAuthorised()`, `tile_visible()`, `check_subtab_persmission()`
- AJAX routes through centralized handlers using `$_GET['fill']` or `$_GET['action']`
- `IS_AJAX` constant (defined in bootstrap): `'AJAX'` or `'NO'`

### OO mysqli Preferred
```php
$dbc->query("SELECT ...")
$dbc->real_escape_string($val)
```

### External Connections
- Use try/catch for external connections (email servers, APIs, payment gateways)
- Never let an external service failure crash the page

### Configuration System
- All system configuration lives in the `general_configuration` table
- Read with `get_config($dbc, 'key')`; write with `set_config($dbc, 'key', 'value')`
- `load_config($dbc, [...])` provides hardcoded defaults when a config row does not exist
- Configuration values from the DB are safe — do not re-sanitize
- **Generic config save endpoints** (no per-tile handler needed): `ajax_all.php?action=general_config` (plain value), `action=general_config_htmlentities` (HTML-encoded value), `action=general_ticket_type_config` (per-ticket-type), and `fill=ajax_save_general`. New config-page inputs should route through these rather than a bespoke handler unless writing to a non-`general_configuration` table

### config_safe_str() — Key Suffix Normalization
`config_safe_str($string)` normalizes a value for use as a config key suffix. If a key is *saved* using `config_safe_str()` on the suffix, the *reader* must also apply `config_safe_str()` to the lookup value:
```php
// Correct — matches how the settings UI saved the key
get_config($dbc, 'ticket_default_program_timeframe_' . config_safe_str($ticket_type));
```

### New Functionality Rules
- **Configuration-first**: All new features MUST be controlled by a configuration option that defaults to OFF, unless the ticket explicitly states otherwise. Never add always-on functionality with no toggle. For ticket features the config must be added to BOTH `Ticket/field_list.php` (options array) AND `Ticket/field_config_field_list.php` (the checkbox UI in the Configuration Gear)
- **Security privileges**: When adding new restricted functionality, always create a NEW security privilege — never reuse existing ones (reusing creates conflicts that break for new customers)
- **Cross-tile features**: When a feature spans multiple tiles (Estimates, POs, Tickets, Invoicing), each tile needs its OWN config toggle and its OWN security privilege — never use a single global config/privilege
- **Match existing patterns**: Do not introduce new paradigms (no frameworks, no Composer packages, no new build tools)

### Configuration Page Navigation — Two Patterns
New and restyled configuration pages must use the **left-tab sidebar auto-save** pattern, not the outdated top-button form-submit pattern.

**Correct pattern (left-tab sidebar, auto-save):**
- Container: `<div class="tile-sidebar sidebar sidebar-override hide-titles-mob standard-collapsible">`
- Tabs: `<a href="?settings=X"><li class="active blue">Tab Name</li></a>` inside a `<ul>`
- Auto-save: `general_configuration` inputs use `onchange="set_configuration(this);"` (shared AJAX handler); checkbox groups add `data-concat=","`
- Reference implementations: `Ticket/field_config.php` (sidebar), `Documents/field_config_default_folders.php` (auto-save)

**Outdated pattern (avoid for new work):** top `<button class="btn brand-btn">` tabs, a `<form method="post">` wrapping all content, and a `<button type="submit">` at the bottom.

**Conversion guidance:** remove the `<form>` and submit button and the POST handler; add `onchange="set_configuration(this);"` to `general_configuration` inputs; for custom (non-`general_configuration`) tables, write a dedicated AJAX handler since `set_configuration()` only writes to `general_configuration`.

### AJAX Patterns
- Avoid reloading the entire page — use AJAX to reload only the section that needs updating
- When adding a new entry, nothing should be added to the database until a detail is entered (e.g., a name or business)
- AJAX responses: HTML for page insertion, JSON with a `status` attribute, or empty/no response are all acceptable existing patterns. New endpoints should prefer JSON with a status indicator (guideline for new code, not a blocker)
- AJAX should use the full URL path for referenced files
- An error callback on `$.ajax()` / `$.post()` write calls is recommended — flag as Minor when missing, never Major or Critical

### Reports Embedded in Tiles
When a report is embedded inside a tile as a sub-tab, the parent tile case sets `$search_options = '0'` and pre-populates the filter POST variable. In this scenario, the parent-tile search field must NOT display (the user is already in that context). Wrap it:
```php
if(!isset($search_options) || $search_options != '0') {
    $search_fields[]['project'] = array(...);
}
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

### SQL Injection Prevention
- **Prepared statements preferred** for user input
- **Non-prepared acceptable** when ALL variables are sanitized:
  - `FILTER_SANITIZE_NUMBER_INT` for numeric values
  - `(int)` or `(float)` type casting for numbers
  - `mysqli_real_escape_string()` for string values
  - `sanitize_input()` for string sanitization
- **Database-sourced values are safe from a sanitization standpoint** — no re-sanitization needed. HOWEVER, a DB-sourced string concatenated into a query STILL needs `real_escape_string()` for SQL *syntax* safety (a value containing a quote breaks the query). Escaping for syntax ≠ re-sanitizing for XSS — the two are different concerns
- **Never** concatenate unsanitized `$_GET`, `$_POST`, `$_REQUEST` directly into SQL
- **Only flag SQL injection** when user input is directly concatenated with zero sanitization
- **SQL identifiers** (column/table names): validate against a hardcoded whitelist array before use:
  ```php
  $allowed_columns = ['first_name', 'last_name', 'email_address'];
  if (in_array($field_name, $allowed_columns)) {
      $dbc->query("UPDATE `contacts` SET `$field_name`='$field_value' WHERE ...");
  }
  ```

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

## Security Standards

### Input Validation
- Validate all user input — type checking, whitelist validation, length limits
- Sources needing sanitization: `$_POST`, `$_GET`, `$_REQUEST`, `$_FILES`
- Sources NOT needing sanitization: DB query results, `get_config()`, `get_contact()`, session values
- Always use `isset()` before accessing `$_POST` / `$_GET` keys
- Numbers: `intval($val)` or `(int)` cast
- Numeric IDs: Always use `FILTER_SANITIZE_NUMBER_INT` (never `FILTER_SANITIZE_FULL_SPECIAL_CHARS` on numeric fields)
- Strings: `sanitize_input($val, FILTER_SANITIZE_FULL_SPECIAL_CHARS)`
- Dates: `date('Y-m-d', strtotime($val))`
- **Dates that drive automated actions** (auto-archive, auto-email, status transitions, expiry checks): `strtotime()` returns `false` on invalid input, which makes `date()` produce `'1970-01-01'` — a past date that immediately fires the action. Always check the result before storing: `$ts = strtotime($val); $date = ($ts !== false) ? date('Y-m-d', $ts) : null;`
- An `(int)` / `intval()` cast on a numeric user input IS acceptable sanitization — do not require it be replaced with a filter

### File Upload Security
- Use `file_safe_str($filename, $folder)` (in `function.php`) for uploaded file names — it strips unsafe characters AND appends a numeric suffix if the file already exists in the target folder (safety + uniqueness). This is the authoritative function; `unique_filename()` does not exist
- Store uploads in the `download/` directory
- Validate file size against expected limits
- Use `move_uploaded_file()` — never copy/rename directly from tmp
- Check `$_FILES['field']['error']` before processing
- **Never trust the client-supplied MIME type or filename** — validate the extension against an allow-list and, where it matters, verify actual file contents; the browser-reported type is user-controlled

### Output Escaping
- HTML context: `htmlspecialchars()`
- URL context: `urlencode()`
- JavaScript context: proper escaping
- SQL context: prepared statements or `real_escape_string()`
- **XSS analysis is skipped in QA reviews** — output escaping is handled at render time per the established codebase approach

### Authentication & Authorization
- Always verify user permissions before operations
- `checkAuthorised()` immediately after `include_once('../include.php')` on every endpoint
- **Verify the tile-name string passed to `checkAuthorised()` is correct** — an incorrect/misspelled tile name silently denies access to ALL users (it does not error), so a typo looks like a broken page rather than a permission bug. Confirm the string matches the tile's registered name by grepping the module before you use it — `grep -rn "checkAuthorised(" --include="*.php" <TileFolder>/` — and reuse the exact string that module already uses. Tile names are not derivable from the folder name or the UI label (`'purchase_order'` not `'purchasing'`, `'reports'` not `'report'`)
- **`$guest_access = true` is a full authentication bypass.** It is correct only for genuinely public pages (public forms, cronjobs, featured galleries). It must NEVER appear on a configuration, admin, or settings page. When testing with curl, a `200` vs a `302` redirect distinguishes a bypassed page from an authenticated one
- **Slider / iframe includes are the established exception:** files loaded via `overlayIFrameSlider` (e.g. `project_create_inventory.php`, `scope_create_po_vendor.php`) do NOT call `checkAuthorised()` directly — they rely on the parent page having already authenticated the user. Do not flag a missing `checkAuthorised()` in slider/iframe includes during QA. Exception to the exception: a file that includes `config.php` (e.g. `Project/config.php`) handles authorization internally
- Never rely on UI hiding alone for security
- Field-level encryption via `encryptIt()` / `decryptIt()` for sensitive data
- Field-level permission enforcement is client-side only — known architectural limitation

### Encrypted Fields Cannot Be Queried in SQL
Encrypted columns (e.g. `contacts.first_name`, `contacts.last_name`) store ciphertext. You CANNOT use SQL `CONCAT`, `LIKE`, `SUBSTRING`, `LOWER`, `ORDER BY`, or comparison on them and expect meaningful results — decrypt in PHP after fetching. Name search/sort must happen in PHP on the decrypted value (this is why list endpoints filter the search term in PHP after loading, not in SQL).

### Session Context
- `$_SESSION['contactid']` — logged-in user's ID
- `$_SESSION['main_contactid']` — real user when impersonating
- Session cookie lifetime is 518400 seconds — do not shorten it in new code
- MySQL session variables (`@contactid`, `@real_user`, `@ip_address`) set in bootstrap for trigger auditing

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

---

## JavaScript Standards

### Compatibility
- Use `var` over `let`/`const` unless browser support is confirmed
- Flag a `const` that is later reassigned (fails silently / errors depending on engine) — prefer `var`
- Avoid arrow functions (`=>`) if legacy browser support needed
- No ES6 default parameters (`function fn(x, y = true) {}`) — write the default explicitly: `function fn(x, y) { if (y === undefined) { y = true; } }`. Flag a default parameter if introduced
- Use `$.ajax()` — avoid `fetch()` without polyfill confirmation
- Always use `encodeURIComponent()` when building URLs with dynamic values:
  ```javascript
  url: 'page.php?tile_name=' + encodeURIComponent(tile_name) + '&category=' + encodeURIComponent(category)
  ```

### Event Binding
- Delegated events for dynamically loaded content: `$(document).on('click', '.selector', fn)`
- Avoid inline `onclick` attributes — use unobtrusive JavaScript (complex inline JS belongs in a separate file as a function)
- Use namespaced events with `.off()` before `.on()` to prevent handler stacking

### Dynamic Widget Initialization
jQuery UI widgets (datepickers, etc.) must be initialized AFTER content is appended to the DOM and guarded against double-init:
```javascript
$('.table_div:visible tbody .datepicker').not('.hasDatepicker').datepicker({ changeMonth: true, changeYear: true, dateFormat: 'yy-mm-dd' });
```
The `.not('.hasDatepicker')` guard prevents re-initializing widgets that already exist when new rows are added. Datepicker variants are differentiated by CSS class in `js/custom.js` (e.g. `datepicker` = year −90→+10, `datefuturepicker` = year→+10, `birthdatepicker` = year −120→+10). Adding a NEW datepicker variant requires (1) its own init block (destroy/guard first) AND (2) appending `.not('.newclass')` to ALL existing datepicker selector chains so the new class is not double-initialized by the generic ones.

### Inline Dashboard Save Pattern
`set_field_value()` is the shared inline-edit save helper — an editable dashboard cell carries `data-table`, `data-id-field`, and `data-id` attributes and calls `set_field_value(this)` on change to persist a single field without a full save. Reuse it rather than writing a bespoke per-cell AJAX save. Every editable `<input>`/`<select>` in `dashboard_load.php`-style files MUST carry all four hooks:
```php
echo '<input name="field_name" value="..." data-table="table_name" data-id-field="id_column" data-id="'.$row['id'].'" onchange="set_field_value(this);" />';
```

### AJAX Error Handling
An error callback on `$.ajax()` / `$.post()` write calls is recommended (flag as Minor when missing, never a blocker):
```javascript
$.post('endpoint.php', data).fail(function() {
    alert('An error occurred. Please try again.');
});
```
Use `async: false` ONLY for must-complete operations (e.g., save before page navigation).

### DOM Safety
- Check element existence: `if ($('#el').length)`
- Escape user-generated content before DOM insertion
- `.every()` on empty arrays returns `true` — guard with `arr.length > 0 &&` first
- Lists populated from an AJAX response must be `.sort()`'d **unconditionally** before render — do not sort only when a search term is present, or the unsearched list comes back in arbitrary DB order: `list.sort(function(a, b) { return a.full_name.localeCompare(b.full_name); });`
- List-init helpers such as `initInvList()` expect a **jQuery-wrapped** element — call them as `initInvList($('.selector'))`, not with a raw selector string or DOM node, or they silently no-op

---

## CSS Standards

- No inline styles on screen (exceptions: `display:none` for JS toggling, PDF output via TCPDF, progress bar width/color)
- Colors defined ONLY in theme stylesheets — never inline and never in `software_wide_style.css` (applies to the style attribute and to height/width attributes)
- `software_wide_style.css` defines size/position attributes only
- Never use `!important`
- All size units in vh/vw or em — never px
- JS functional selectors (underscore-separated) and CSS styling selectors (dash-separated) are intentionally distinct
- **Reuse existing utility classes instead of inline styles.** Known helpers: `border-ddd`, `pad-10`, `force-pad-10`, `offset-bottom-5`, `offset-left-10`, `text-grey`, and `panel-body` (light `#fafafa` panel background). Prefer these over an inline `style=""`
- **Selector compatibility:** `:has()` requires Chrome 105+ — avoid it where older browser support matters. `:not(td)` is valid CSS; `:not('td')` (quoted) is invalid and silently fails — never quote the argument to `:not()` in a stylesheet

---

## HTML Standards

- Meet W3C standards (testable at validator.w3.org)
- No whitespace before the first `<?php` or `<html>` tag
- Add comments at the closing tag for longer divs/spans
- Double quotes for all HTML tag attributes (`name="example"`)
- Do not use HTML `id` attributes — select by class, type, and relative position. Legacy exception: the `#no-more-tables` responsive-table id is established and acceptable
- `src` attributes reference the FQDN: `<img src="<?= WEBSITE_URL ?>/img/icons/EXAMPLE-add-icon.png">`
- Never use short open tags (`<?`) for output — use `<?=`. `<?` depends on the `short_open_tag` ini setting and silently outputs nothing when disabled
- Table column count: when a `<th>` is conditionally rendered, the corresponding `<td>` must use the exact same condition

---

## PDF

- TCPDF is used to generate PDF files
- Supported CSS is limited — inline styles are acceptable here (and only here)
- For PDFs that embed/import existing PDF pages, the MYPDF class extends `\setasign\Fpdi\Tcpdf\Fpdi` (see `Estimate/estimate_pdf_output.php`)

---

## Error Handling

- Never show raw PHP errors/warnings to end users
- Functions return predictable types on failure (empty array, false, null)
- External connections wrapped in try/catch — never let an external service failure crash the page
- Always return valid JSON from AJAX endpoints with a success/error indicator

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

## Debug Code — Remove Before Submitting

Search for and remove:
- `console.log(`
- `var_dump(`
- `print_r(`
- `if(true)` / `if (true)`
- `1==1`

For reliable local debug output prefer `file_put_contents('/tmp/debug.log', ..., FILE_APPEND)` over on-page dumps.

---

## Restricted Folders (Never Modify)

Never make changes in submodules or these folders:
`lib`, `PHPExcel`, `php-excel-reader`, `tcpdf`, `fpdi2`, `fpdf181`, `FPDI-1.6.1`, `mrbs`, `oauth-php`, `swiftmailer-5.x`, `swiftmailer-calendar-master`, `tinymce`, `tinymce_5.0.6`, `tinymce_7.0.1`

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

## Standards Enforcement Scope

- These standards apply ONLY to **new code** being added. Minor changes to existing lines do not require rewriting surrounding code to comply.
- Coding and styling standard violations are **NEVER Critical** (unless they independently cause a fatal error or security vulnerability). They are:
  - **Major**: when the violation causes a functional problem, breaks theme compatibility, or creates a maintenance burden (inline colors themes can't override, duplicated code blocks, missing function comments on complex functions)
  - **Minor**: when the violation is cosmetic or a best-practice preference that doesn't affect functionality (spacing, px instead of em, missing comment on a simple function, pagination vs scroll-to-load choice)

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

## Scrolling Rules

- Pages should not scroll — only the content area scrolls
- Never have overlapping/nested scrollbars (vertical within vertical, or horizontal within horizontal)
- If an exception is needed, confirm with the project lead

---

## Local Dev Environment (Reference)

- Local PHP runs 8.1; `error_reporting(0)` is set — runtime warnings are suppressed on-page, so check the PHP error log (`/var/log/php8.1_errors.log`) rather than relying on screen output
- `localhost:80` serves the feature branch under test; `localhost:81` serves the production baseline for side-by-side comparison
- PHP-FPM caches compiled bytecode — restart FPM after editing PHP files or switching branches, or changes appear to have no effect
- A lightweight unit-test harness exists at `AdminSettings/unit_tests.php`
- MySQL `sql_mode` should be empty locally to match production behaviour — a non-empty `sql_mode` (e.g. `ONLY_FULL_GROUP_BY`, `STRICT_TRANS_TABLES`) makes queries fail locally that run fine in production, producing false QA failures

---

## UI / UX Style Guide (New Code Only)

These are team-wide UI guidelines for new functionality. Violations are Minor unless they break theme compatibility. Document any authorized variation in a PHP comment (who authorized it + ticket number).

### Things Not To Do
- No black box around content; no gray background for content (gray is only for section headings/notes)
- No blue background for accordion content (should be white)
- No inline styles (except `display:none` and PDF output)
- No links in headers — icons only

### General Practices
- When adding a background color, always add a text color for readability
- Use CSS classes, never hardcoded styles (so themes can override)
- Loading content shows the EXAMPLE loading circle (pages, sliders, reloads)
- Search begins only on Search button click
- Icons in headings/labels appear AFTER the text (exception: an icon that represents the heading itself)
- Required-field asterisk appears after the label colon with a leading space (e.g. `List Name: *`)
- Dropdown changes should update/clear dependent fields
- No multi-select fields — use a dropdown with +/x icons to add multiples
- Auto-save fields where appropriate; saving shows a green circle around the home logo (top-left); a "New" entry doesn't save until a detail is entered

### Plus Icon vs Add Button
- Empty section → show an Add button; section with items → show a `+` icon
- Header area → always an Add button (e.g. "Add Ticket")

### Header / Content Header
- Tile header background white; tile title left-aligned; tile-wide icons right-aligned (Reporting/Pie/Dashboard icon first)
- Content header background silver/#ECECEC; title left, quick actions right; >4 quick action icons → Pandora's box

### Tables
- Header in theme color, left-aligned; numeric data right-aligned; sticky header on scroll
- Display headers even when the table is empty
- Alternating rows via `.table-striped` or `.row-even-bg`/`.row-odd-bg`
- Horizontal scroll → scrollbar on both top and bottom; function-column icons centered
- Large row counts may load on scroll instead of paginating

### Slider Table Styling
- Description/name column `width:auto`; other columns a fixed narrow percent (~8%); right-align numeric columns
- Long content uses `overflow-y:auto` on the scroll container (never nested vertical scrollbars)
- Always render the header row; when there are no records show a single full-width row via `colspan` ("No records"), not a blank table
- Skip rows that are both empty and zero when appropriate for the view

### Cards
- Container silver/#ECECEC; card white with border and padding
- Title clickable to edit, format `Item Type #Number: Name`; quick actions below title; email/phone as clickable links; load on scroll

### Sliders (Right Panel)
- White background; `<h3>` title left, red close button right; full-width `<hr>` after header
- Use `get_frame_slider_header(array('title' => '...'))` to render the standard header inside a `standard-body-title` div
- Icons use `.inline-img` (touch-friendly, equal size); tooltips use `.no-toggle` + `title=""` + `data-placement="bottom"`; >4 icons → Pandora's box
- Dropdown selections open in the same slider; other actions open a new slider on top; closing a child slider updates the parent
- Footer: delete (red) left, close X left, save icon before buttons, Submit rightmost
- **Closing a slider:** link to `<?= WEBSITE_URL ?>/blank_loading_page.php` — navigating there triggers `window.parent.$('.iframe_overlay').last().hide()`. There is no `overlayIFrameSlider_close()` and no `parent.closeiFrame()` function
- **Opener signatures:**
  - `overlayIFrameSlider_old(url, width, confirm, reload, height, change_close)` — full 6-argument form (supersedes older 4-arg references)
  - `overlayIFrameSlider({url, no_confirm, no_reload, change_close})` — newer object-argument form
  - **Do NOT pass positional arguments to `overlayIFrameSlider()`** — the object form uses JS destructuring and silently fails when given positional args. Use `overlayIFrameSlider_old()` for positional calls
- A standalone page that opens sliders MUST contain a hidden `.iframe_overlay` template div, or the slider silently fails to appear

### Full View (Edit Screen)
- White header; title format `Tile Name: Item #Number - Name`; sidebar section headings scroll/highlight; sections separated by `<hr />`; on scroll, header collapses to a 3-dots icon
- Footer: red delete left, save icon right with related buttons; all buttons/icons in theme color except Delete (always red)

### Accordion / Mobile View
- Tabs render as accordions, sub-tabs as nested accordions; heading shows count; only one open at a time; tables use `#no-more-tables`; search hidden initially, toggled by 3-dots icon

### Reports (UI)
- Minimum a PDF export button; search fields visible initially, hidden after Search, toggled by 3-dots
- Default date range = start of current month → today; date fields on one row labeled "Date Range:"
- Before search: show "Please Submit Search Criteria"
- PDF: logo, report note, dark header with white text, alternating rows, clickable links

### Encrypted Fields
- Padlock icon after the label (tooltip "Encrypted Field"); read-only by default with the value hidden; eyeball icon when the field has data (tooltip "Field has data")

### Load More Eyeball
- Show the latest 10 records with an eyeball icon for more (visible only when more exist); click opens a right slider; >25 records → paginate within the slider

### Receipt Builder / Side Panel
- Collapsible by dragging the separator bar (center expands when collapsed); white background; independently scrollable; on mobile shown first; negative values in red within brackets `(-12.99)`

### Formatted-Text Editable Fields
- Editable fields wrapped with a `[formatted-text]` marker use a `::before`/`::after` overlay CSS system to show currency/units without altering the stored value; helper `getFormattedCurrency()` produces the display string; the overlay must be suppressed while the field is actively edited

---

## External / Customer-Facing Pages

- Must still use CSS classes from `software_wide_style.css` — no hardcoded colors
- Use the Bootstrap grid for centering (`col-sm-6 col-sm-offset-3`, etc.)
- Logo fallback: check `file_exists()` before using a configured logo, fall back to `img/examplelogo.png`
- Inline styles acceptable only for layout positioning (flexbox, no color/size values) or vh/vw spacing
- Pre-existing footer issues in `$guest_access` context should not be fixed on unrelated tickets

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

---

# Codebase Knowledge (Module Internals)

How the software actually works, organized by tile/system. This is durable architecture — table relationships, function behaviors, config patterns, and recurring traps that apply across tickets. (Individual ticket bug logs, line numbers, and branch names are intentionally excluded.)

## Platform Architecture
- No framework, no Composer autoloading, no MVC, no modern JS bundler. Entry points are standalone `.php` files bootstrapped by `include.php`
- Tile-based: each top-level directory is one feature area. AJAX routes through centralized handlers (`ajax_all.php` and per-tile `*_ajax.php`) via `$_GET['fill']` / `$_GET['action']`
- Multi-tenant: each customer has its own database/instance with its own `general_configuration`, contacts, and data. The same tile behaves differently per customer because labels, statuses, and enabled features are config-driven — always confirm whether a change is global or customer-specific
- A separate cross-software connection `$dbc_htg` exists for "Softwarewide" data via `database_connection_htg.php`
- CRLF line endings throughout
- `run_cronjobs()` in `include.php` executes synchronously on every page load
- Login/auth flow is centralized in `is_login.php`

### Core Helper Functions
- `get_config($dbc, 'name')` — read from `general_configuration` (returns `''` when unset, not null/false)
- `set_config($dbc, 'key', 'value')` — write to `general_configuration`
- `load_config($dbc, [...])` — hardcoded defaults; final fallback is `''` (never null)
- `get_contact($dbc, $contactid, 'field')` — contact data lookup (joins `contacts_cost`, so fields like `pay_terms` resolve)
- `get_field_value($dbc, ...)` — single field value lookup
- `config_safe_str($string)` — normalizes a value for use as a config key suffix (read/write must both apply it)
- `file_safe_str($filename, $folder)` — safe + unique uploaded file names (the authoritative upload function; `unique_filename()` does not exist)
- `tile_visible($dbc, $tile_name)` — tile visibility check
- `IS_AJAX` constant: `'AJAX'` or `'NO'`

### Time Format Display System
- User/system time display format is centralized: `system_time_format` config (12h vs 24h) drives `load_time_user_format()` and the `time_user_format()` helper plus `TIME_FORMAT_PHP`-style constants. Render times through this helper rather than hardcoding `date('H:i')` / `date('g:i A')`, so the customer's configured format is respected everywhere

### Session Context
- `$_SESSION['contactid']` — logged-in user; `$_SESSION['main_contactid']` — real user when impersonating
- MySQL session vars (`@contactid`, `@real_user`, `@ip_address`) set in bootstrap for trigger auditing

### get_contact() Per-Request Cache
- `get_contact()` / `get_contact_shared()` cache in `$_SERVER['values-contacts'][$field_name]['contactid-'.$contactid]`. `$field_name` is `default_field` (no param), `full_name`, `name`, `name_company`, `phone`, or any column name
- The cache is only used when `$dbc === $_SERVER['DBC']` — a secondary connection bypasses it and re-queries every call
- `default_field` builds a composite display string (name/first/last/site/display/nick/position/category) plus `contacts_label`, incognito labels and the position-display config; `full_name` builds `name: first last: site_name` deduped plus nickname and labels. Both are multi-query per contact on a cache miss
- For dashboards, lists and exports, **pre-populate the cache** with one bulk query for all needed contactids and write the results directly into `$_SERVER['values-contacts']` before the render loop — `get_contact()` then returns from memory and the per-row queries disappear

## Configuration & Audit Infrastructure
- **`general_configuration`** — key/value store; read with `get_config()`, write with `set_config()`. The trap: `field_config` tables and `general_configuration` are different stores (`get_field_config($dbc,'tickets')` ≠ `get_config($dbc,'ticket_fields')`); the wrong source returns empty silently
- **`field_config`** — single-row table with one column per tile (`tickets`, `purchase_order`, `inventory`, `time_cards`, …); each column stores a comma-separated list of enabled features/fields. Read via `get_field_config($dbc, 'column')` which returns the list comma-wrapped (`,value,`) for `strpos` matching and caches in `$_SERVER['field_config']` after first read. Configuration Gear checkboxes write here
- **`all_config_history`** — audit of all configuration changes: `table_name`, `config_name`, `prior_value`, `new_value`, `src_script`, `created_by`, `created_date`, `ip_address`. UI changes record the PHP script path + the user's `contactid`; `db_defaults.php` writes `src_script='Admin'`, `created_by=0`, `ip_address='N/A'`. Use it to diagnose when/how a config was enabled and whether it was manual or automated

- **Type ID assignment lives in `db_structure/db_triggers.php`, not PHP.** Invoice `type_id` is set by BEFORE INSERT/UPDATE triggers on `invoice` as `MAX(type_id) + 1` filtered by `YEAR(invoice_date) = YEAR(CURDATE())` — an annual reset by design — falling back to the `invoice_type_id_reset_invoice_type_{type}` config when no rows exist for that year. Ticket `type_id` is set by a BEFORE INSERT trigger on `tickets` using the per-type config (`ticket_type_id_reset_ticket_type_{type}`) or the system-wide `ticket_type_id_reset_system_wide`, also resetting annually via `YEAR(created_date)`. Numbering gaps or duplicates are trigger behaviour — do not chase them in application code

## Multi-Flag System
- `item_flags` — central flag storage (`item_flag_id`, `item_flag_tile_id`, `record_id`, `flag_colour`, `flag_label`, `flag_start`, `flag_end`, `flag_user`, `flagged_by`, `flagged_date`, `deleted`)
- `item_flag_tiles` — maps tile names to integer IDs (`item_flag_tile_id`, `tile_name`, `table_name`, `id_column`)
- `flag_display_inc.php` — shared display include. Set `$flag_tile` and `$flag_record_id` before including; it sets exactly four variables: `$flag_styling` (inline CSS or `display:none;`), `$flag_label`, `$flag_badge` (rendered HTML), `$flag_count` (int). It filters by date internally — do not pre-set `$_flag_start/$_flag_end`. To get a colour, extract from `$flag_styling`; there is no `$_tmp_flag_colour`. `$flag_count` is undefined until after the include
- `get_item_flags($dbc, $tile, $record_id, $active_only)` / `get_item_flags_batch($dbc, $tile, $record_ids)` — function-based API (use the batch version on dashboards to avoid N+1)
- `quick_action_flags.php` — handles all flag writes (add/edit/expire/remove); writes ONLY to `item_flags`. Legacy `flag_colour`/`flag_label`/`flag_start`/`flag_end` columns still exist on tables but are NOT read for display

## Tax Rate System
- `field_config_tax_rates` — `id`, `tax_name`, `tax_rate` (percent), `contactid` (0 = all vendors, >0 = vendor-specific), `tax_code`, `tax_registration`, `gl_code`, `exempt`, `editable`, `deleted`. Set `contactid` to a vendor's id to make a rate appear only for that vendor on POs
- `field_config_tax_details` — `tax_id` (PK), `rate_id` (FK → `field_config_tax_rates.id`), `detail_name` (e.g. "GST", "PST"), `tax_rate` (component percent), `detail_registered`, `gl_code`, `deleted`. QB/IIF export splits total tax proportionally across these detail rows for the invoice's rate
- **Apply-to-cost**: `field_config_tax_details.apply_to_cost_po_types` (CSV of PO categories where the tax is absorbed into item cost) and `purchase_orders_product.apply_to_cost_amount` (calculated amount added to cost per line). Calculated during PO receiving and included in `validate_inv_change_log()` cost queries; PO categories come from `po_tile_split` / `po_tile_split_types_{tile}`

## Configurable Time-Off Column System
- `get_time_off_types($dbc)` — returns type definitions from the `time_off_types` JSON config; each type has `id`, `label`, `input_mode` (`hours`|`fraction`), `behavior` (`accrue_reduce`|`manual`|`record_only`), `deleted`. If the config is empty it auto-migrates from `field_config.time_cards` legacy options
- Balances tracked in `accrued_time_off` (discriminated by `accrued_type`); columns appear on the timesheet via field config keys `timeoff_{id}` (balance) and `timeoff_{id}_used` (entry); save via `Timesheet/time_cards_ajax.php` action `update_time_off_balance`; accrual via `cronjobs/accrual_days.php` ("top up to" = target − current); alerts via `Timesheet/time_off_alerts.php`; type management UI in `RateCard/field_config_rates.php` (accrual dropdown filtered to `accrue_reduce` types)

## Software Theme System
- Theme CSS: `css/style_[theme_key].css` (full compiled CSS, ~5000–7800 lines each); background images under `img/[theme_key]_theme/`
- A new theme must be registered in THREE files: `header.php`, `login_page_style.php`, `Settings/style_config.php`
- Selection stored per-user in `contacts.software_styler_choice`, software-wide in `general_configuration.software_default_theme`, and per-security-level in `field_config_security_level_theme.theme`
- The brand colour appears ~60 times per theme CSS (body background, `.brand-btn`, `th`, sidebar active states, `.brand-color`, `h3/h4`, `footer`, `.brand-nav`)

## API System (`Api/`)
- JSON REST endpoints served from `Api/data.php` (and siblings). Calls are logged/tracked in the `api_calls` table(s). Any change to a response shape is a public contract change — coordinate with consumers before altering keys or types
- Config/audit tables: `api_calls` (defined endpoints), `api_call_options` and `api_call_values` (per-call parameter/field definitions), `api_call_history` (invocation log). Endpoints are typed by template — reuse an existing call template type rather than inventing a new response shape

## Settings & Navigation (`Settings/`)
- Central settings tabs, logo uploads, and the global action slider live under `Settings/`. Theme registration touches `Settings/style_config.php` (see Theme System). The global quick-action slider's contents are driven by `quickactionicon_config` (per-tile/role action icons) — add a new global action there rather than hardcoding it into the navigation

- **Dashboard default selection** (`home.php`): `tile_dashboards` holds `dashboard_id`, `name`, `tile_sort` (`#*#`-delimited tiles), `default_levels` (security levels defaulting to this dashboard), `assigned_users` (a single contactid, or NULL for everyone), `restrict_levels`, `deleted`; `contacts_tile_sort.default_dashboard` holds the user's own choice. Priority: (1) an explicit `?dashboard_id=X`, (2) the personal default from `contacts_tile_sort`, (3) a role match in `default_levels` (a comma-bounded LIKE) — the code walks the user's roles in order and the first role that returns a row wins. A personal default overrides the role default permanently until changed, which is the usual explanation for "the wrong dashboard keeps loading". `assigned_users` restricts a dashboard to one contactid; a role listed in `restrict_levels` cannot see the dashboard selector at all (locked to its assigned dashboard), and the selector renders only when none of the user's roles appear in any `restrict_levels` entry

## Short URL System
- A short-URL/redirect mechanism exists for shareable links (customer-facing tokens resolve to full internal URLs) — reuse it rather than building ad-hoc link shorteners

## Slider / Utilities
- Slider files: place in the module folder, `include_once('config.php')` (NOT `../include.php`), do NOT use `ob_clean()`; close by linking to `<?= WEBSITE_URL ?>/blank_loading_page.php`; open via `overlayIFrameSlider_old(url, width, confirm, reload, height, change_close)` or the object form `overlayIFrameSlider({url, no_confirm, no_reload, change_close})`. Slider files rely on the parent for authentication and do not call `checkAuthorised()` directly. A standalone page that opens sliders must include a hidden `.iframe_overlay` template div. Use a `no-more-tables` wrapper with `data-title` for responsive tables. Render the standard header with `get_frame_slider_header(array('title' => '...'))`
- Image resize: ratio-scale with `imagecreatefromstring` + `imagecopyresampled`, preserve PNG/GIF alpha (`imagealphablending(false)` + `imagesavealpha(true)`), output by extension (png/gif/jpeg quality 90)

---

## Ticket / Programs / Work Orders (`Ticket/`)
- Core table `tickets` (100+ fields). Related: `ticket_attached` (multi-purpose line items — staff, inventory, services, equipment, communication), `ticket_schedule` (stops/deliverables with routing), `ticket_comment` (threads), `ticket_checklist` (dynamic checklist items), `ticket_attached_membership` (classification rows for programs)
- Organized by **ticket types** (tabs), configured via `ticket_tabs` in `general_configuration`. Each type has its own accordion layout, field visibility, security. Per-type field config stored as `ticket_fields_{type}`; read per-type config via `get_config($dbc, 'config_key_' . config_safe_str($type))`
- **`field_config_ticket_fields` authority:** the per-type row is authoritative for field enablement and sort order; the `ALL` row governs enablement only, NOT per-type ordering. When reading a field's position, read the per-type row
- Accordion UI: 50+ collapsible sections defined in `field_list.php`
- Staff has TWO views: **Staff accordion** (`add_ticket_staff_list.php`, non-schedule staff `sched_id=0`, numeric inputs, config prefix `Staff *`) and **Plan/Schedule view** (`add_ticket_plan.php`, schedule-based staff, timepicker inputs, config prefix `Plan *`)
- **Contract contacts**: `tickets.contract_contact1_id` … `contract_contact6_id` hold up to six additional contract-side contacts
- **Field meanings**: `qr_code_scanned` records a QR check-in; `gps_30_min` tracks the 30-minute GPS ping state
- **View-only rendering**: `viewonly_fields` + `setViewOnlyFields()` (JS) and the `view_profile` flag drive a two-render-block pattern — a read-only block and an editable block; keep both in sync when adding a field. `preventSave` / `manualSave` CSS classes control whether a field auto-saves
- **Billing hours fallback**: billable hours resolve as `IFNULL(NULLIF(bill,0), hours)` — an explicit `bill` of 0 falls back to tracked `hours`
- **Text editors / `cust_details`**: ticket detail sections are stored in `cust_details`, delimited by section codes (`SD`, `RP`, `DQA`, etc.) split on `*#*` then `##*##`. Rendering multiple rich-text editors on one ticket has known initialization-order hazards — initialize each editor after its container is in the DOM
- `force_readonly` blocks edits once an invoice exists (gated by "Edit After Invoice" config)
- `alert_users()` in `Ticket/ticket_functions.php` sends registration/confirmation email + ICS (when `calendar_invite=1`); alert config in `field_config_ticket_alerts` per type; time priority `member_start_time` > `to_do_start_time` > classification-level
- **Digital forms on a program**: key `project_digital_form_[projectid]_[type]`; forms defined in `user_forms` (`form_id`, `name`)
- **Unassigned tab**: configs `ticket_unassigned_options`, `ticket_unassigned_status_name`, `ticket_archive_status`, `tickets_dashboard`
- **Pieces**: `ticket_attached` rows with `src_table='inventory_general'`; transport logs in `ticket_schedule` with `piece_details` (CSV of piece IDs) and piece shipping/brokerage/insurance stored as CSV per stop. CSV index matches UI sort order (`LPAD(sort_order...)`), NOT `ORDER BY id`. A single `posproductid` can appear as pieces across multiple tickets — piece-total recalculation must sum across ALL tickets and stops before writing PO header totals
- **Piece TARE model**: `is_tare` / `tare_id` / `main_id` link a tare (container) piece to its content piece; config `ticket_piece_qai` toggles piece return / copy_piece / tare_weight / carrier_api behaviors
- **Piece fee distribution** (shipping/insurance/brokerage across pieces) uses a cost-based proportional formula (fee × piece_cost ÷ total_cost), not a flat even split
- **Piece → inventory auto-creation**: gated by the `Inventory General Piece Creates Inventory` value in ticket field config. The `update_fields` action (and `copy_all_pieces` during bulk copy) auto-INSERTs an `inventory` record named "Piece #[ticket_attached.id]: [piece_type]" when editing/copying an `inventory_general` piece; duplicate-prevented via a subquery checking existing inventory with the same `ticket_attached_id`
- **Shipping Orders** (ticket type): transport-log stops in `ticket_schedule` have `deleted=20`, linked by `sched_id` to a parent stop; piece Delivery/Insurance/Brokerage amounts all save back to `purchase_orders_product` and re-sum into the PO header
- Deliverable Accordion Mode requires "Plan Multiple" enabled AND more than one stop; panels lazy-load on heading click
- Adding a new ticket field: add option to the accordion array in `field_list.php`; add rendering to the accordion include (both view-only and editable blocks); add to `field_config_field_list.php` for the config UI; update `get_ticket_field_label_by_config_name()`; add save logic to `ticket_ajax_all.php`
- **Renameable field labels**: labels shown on a ticket can be customer-renamed via the `update_field_name` action → `set_config()` where the config key IS the field's config name and the HTML carries a `data-default` fallback label. Read the label with `get_config()` falling back to `data-default`, never hardcode the display text
- **Field sort with unstored fields**: when computing field order, fields that are enabled but have no stored sort position append at the END (never interleaved among positioned fields); the per-type sort query returns NULL when no row exists for that type. For `db_defaults.php` edits to a field list, use `FIND_IN_SET` plus comma-bounded `REPLACE`/`TRIM` so you match whole values only
- **Piece → PO mapping**: piece-table columns for Shipping/Insurance/Brokerage save back to `purchase_orders_product`; after editing pieces, the PO header is re-summed by `recalculate_piece_po_totals()` — a single `posproductid` can appear as pieces across multiple tickets/stops, so the recalculation must sum across ALL of them before writing header totals
- **Support questions**: per-type config `support_questions_{config_safe_str(type)}` (`*#*`-delimited) defines questions; answers are stored in `tickets.cust_details` as `Label##*##Answer*#*...` and rendered through the `cust_details` section codes
- **`cust_details` section codes**: ticket detail sections are stored in `cust_details`, split on `*#*` then `##*##`, keyed by section codes (`SD`, `RP`, `DQA`, `TEN`, `IUXR`, `DRR`, `DRA`, etc.). When rendering multiple rich-text editors on one ticket, initialize each editor only after its container is in the DOM (known initialization-order hazard)

## Estimate (`Estimate/`)
- `estimate` (main), `estimate_scope` (line items), `estimate_scope_heading` (headings). Scope items typed by `src_table` (equipment, inventory, labour, material, services, products, vpl, notes, miscellaneous). Miscellaneous items have `src_id=0` with text in `description`
- Scope monetary fields are `est_retail` / `retail` — there is NO `est_total` / `total` column on scope (a common wrong-column trap)
- Scope field configuration is loaded once per request into `$_SERVER['scope_fields']` (from `field_config_scope_fields.php`) — read from that request cache rather than re-querying the config in scope loops
- `estimate_field_order` config: `#*#`-delimited, each field `FieldName***Label***extras`
- UoM fields: hidden `<select>` + hidden `<input>` sharing `name="uom[]"`; disabled element doesn't submit. Destroy select2/chosen before cloning DOM, re-init after appending
- Optimized loading: client-side batched rendering — all rows returned in one response, JS injects in chunks of 5 `<tr>` via `setTimeout(0)`
- Two history tables: `estimates_history` (main change log, `updated_by` = name string — use for reporting) vs `estimate_history` (status audit, `updated_by` = contactid)
- RFQ pricing: `estimate_scope.posproductid` links to selected PO line; competing PO lines marked `deleted=2`
- **RFQ — Preferred Vendor split**: the `build_rfq` action supports `split: 'preferred_vendor'` — joins `preferred_vendors` to `estimate_scope`, keeps items with exactly one preferred vendor and not already on an RFQ, groups by `vendorid`. `purchase_orders.estimate_sort` orders RFQs in sliders. Item management actions: `get_unassigned_scope_items`, `add_items_to_rfq`, `rfq_move_item`, `rfq_add_item`, `rfq_remove_item`; cross-PO drag/drop via jQuery UI `sortable` (`connectWith: '.sort_table2'`)
- **PDF attached documents**: `Estimate/estimate_pdf_documents.php` helpers + `estimate_pdf_output.php` MYPDF extends `\setasign\Fpdi\Tcpdf\Fpdi` (for page embedding); gated by the "Attach Documents" field-config token; 4 placement points (before_title, after_title, after_details, end_of_document) using `estimate_document` fields `include_in_pdf`, `pdf_sort_order`, `pdf_placement`
- Conversion to project (`convert_to_project.php`) merges scope into an existing project when `add_to_project > 0`; addendum estimates link back to the originating project

## Project (`Project/`)
- `projects` (main), `project_scope` (line items), `project_scope_heading` (headings), `project_path` (milestones), `project_billing`. Milestone path templates live in dedicated path-template tables
- Cost semantics: `project_scope.cost` = planned cost (never overwritten by PO actuals), `actual_cost` = actual from PO receiving, `price` = sell price (applied to `ticket_attached.rate`)
- `inventory_wip_mode` config governs how project WIP inventory is treated
- `allocate_scope_items()` in `function.php`: creates scope rows from unallocated `ticket_attached` rows and PO line items, syncs `actual_cost`/`actual_qty`; must not duplicate a scope row when a `posproductid` already has one (`added_from_po_line`)
- Tab-based UI per project type via `field_config_tabs.php` (tabs: Info, Scope, Path, Billing, Summary, Communication, Report, Inventory, Accounting); visibility stored as `project_tabs_[type]`
- Saving config from project tabs: `$.post('../ajax_all.php?action=general_config', {name, value})`; `initSave()`/`doneSaving()` NOT available in project-tab context; init select2/chosen with `initInputs($('body'))` on ready
- WO date calculation: waterfall scheduling via `advance_to_business_day()` (skips weekends + holidays); "Create WO per Milestone" computes dates, plain "Create Work Order" checkbox leaves them blank
- Adding a new project tab: create `Project/edit_project_[tab].php`; route in `edit_projects.php`; sidebar link in `edit_projects_desktop.php`; register in `field_config_tabs.php`; enable via tile Configs → Tabs

## Purchase Order (`PurchaseOrder/`)
- `purchase_orders` (header: `posid`, `status`, `delivery` freight, `brokerage_amount`, `insurance_amount`, totals, `contactid` vendor, `projectid`, `warehouseid`), `purchase_orders_product` (line items: `posproductid`, `quantity`, `qty_received`, `additional_qty_received` excess, `price`, fee columns, `apply_to_cost_amount`, `ticketid`, `projectid`, `auto_received`)
- Statuses (from `po_tabs`): RFQ, Estimated, Real-Time, Pending, Pending Approval, Receiving, Paying (shown as "Accounts Payable"), Processed - Not Paid, Paid, Back Ordered, Completed
- **Progressive loading**: PO dashboards load lists progressively and cache the sidebar; per-type PO label/number templates are stored in config
- PO line rendering uses `do { ... } while($prod_line = ...->fetch_assoc())` so the template row always renders once — do NOT wrap in `if($prod_line)`
- Auto-receive: `po_auto_receive_statuses` CSV; `po_auto_receive_get_items()` atomically flags items `auto_received=1` to prevent duplicate receives across its three callers (dashboard AJAX, cronjob, form POST). Excess receiving splits the line, `additional_qty_received` tracks excess
- **Two-stage receiving** with a MAX Bin Alert: receiving caps to pending qty unless `excess=1`; a bin-capacity alert warns when a received qty would exceed the bin's configured maximum. A staging column `purchase_orders_product.received` holds the in-progress received qty before it is committed to `qty_received`; long receives report progress via `receiving_progress.php`. An item's `inv_status` is derived from `wip_status` (a `wip_status > 0` item is treated as WIP with cost forced to 0). The MAX Bin Alert check (`po_max_bin_alert_check()`) compares the resulting bin quantity against the bin's configured maximum and returns the alert state
- **Two payment-term systems coexist**: the legacy `po_payment_terms` config (`Name|Days` entries, `#*#`-delimited) AND the newer `ratecard_payment_terms` table (`rate_type` of `company` or `contact`). A vendor's default term is stored in `contacts_cost.pay_terms` as the term NAME text, not an id — resolve by name, and cascade vendor default → system default
- Receiving (`fill=rec_po`): updates `qty_received`, creates/updates `ticket_attached` for WOs, updates `project_scope.actual_qty`. **Warehouse → bin resolution**: the receiving handler reads `warehouseid` from the PO header and resolves `qty_id` via `inventory_qty WHERE inventoryid=… AND IFNULL(NULLIF(warehouse,0),'')='$warehouseid'`, creating the `inventory_qty` row if none exists. **Serialized items**: when `$inv` is swapped from child to parent `main_inventoryid`, the parent's `qty_id` must be re-looked-up and applied (both `process_po_receive` and `rec_po`) or log entries record against the wrong bin
- **Qty validation**: status advancement from Pending is blocked when content-bearing line items have null/empty/0 `quantity` (blank placeholder rows excluded); enforced in `add_point_of_sell_save.php`, `dashboard_load.php`, and `purchase_order_ajax_all.php` (`checkPoQty` + `checkNextStep`), with a client-side `checkPoQty` AJAX before submit
- `po_total_calculate()` sums line items into header totals; Financial Slider (`po_financials.php`) gated by `approval_privilege`; receiving-fee access gated by `receive_deliver`/`receive_broker`/`receive_insurance`
- **PDF currency display**: `po_pdf_currency_display` config (`never` default / `always` / `foreign_only`); `get_po_pdf_currency_prefix($dbc, $posid)` resolves currency from `purchase_orders_product` → `purchase_orders` → `purchase_order_currency` system default and returns a prefix (e.g. "USD ") applied to Sub Total/Total in all 6 designs (`foreign_only` only shows when PO currency ≠ system currency)
- Back Order: `main_posid` → parent, `back_ordered=1`, label suffix `-B{n}`. RMA: `rma_po` stores source posid, `rma_flag=1`, label prefix `RMA-`, does NOT set `main_posid` (so RMAs don't appear under a parent's dashboard search; back orders do)
- 6 PDF designs in `create_pos_pdf.php` (Design 6 = Can-Seed), chosen per category; designs defining two PDF classes need header/footer changes in both
- **Sidebar prefetch pattern**: the PO sidebar (`PurchaseOrder/sidebar.php`) uses `get_prefetched_contact_list($status, $field)` and `get_prefetched_contact_list_all($field)` to run a few bulk queries upfront and distribute results to every status/subtab section (business, site, warehouse, vendor), plus `$_prefetch_date_received` and `$_bo_posids`/`$_bo_contact_counts` precomputations. Replacing these with per-section `sort_contacts_query($dbc->query(...))` re-creates 40+ queries per load — always use the prefetch functions in the sidebar. `sort_contacts_query($result, $sort_field='full_name')` (computes `full_name` handling prefer/first/last/name) is the acceptable inline alternative for single-use queries only, never in repeated sections. Sidebar warehouse loops filter hidden warehouses via `if(!empty($hidden_warehouse_names) && in_array($warehouse['name'], $hidden_warehouse_names)) { continue; }` — do not remove. Credit Memos are POs with `credit_memo_flag=1`; the Credit Memo tab excludes Completed ones (they appear in Completed POs)

---

- **Split tiles**: `po_tile_split` config holds the tile names (`#*#`-delimited); `po_tile_split_types_[config_safe_str(tile_name)]` holds that tile's comma-separated PO types. `config.php` resolves `$current_tile_group` from `$_GET['tile_group']` or the referer, matches it against the split names, sets `$po_type_limit` and builds `$po_type_query` (plus `$po_type_query_alias` for queries aliasing the table as `po`). The filter is appended to `$filter_query` in `dashboard_load_list.php` and `summary.php`, so every summary block inherits it. **Exception:** the warehouse summary block uses a LEFT JOIN — the filter must go in the ON clause, not the WHERE, or warehouse counts drop rows
- **Dashboard list caching**: file-based cache at `DOCUMENT_ROOT/../cache/cache_po_[config_safe_str(WEBSITE_URL)]_[md5($filter_query)]` holding serialized items keyed by posid plus `last_modified` and `cache_version`. A warm hit requires the file to exist, to have been modified today, to hold more than 10 items and to match the current version; the warm path only reprocesses POs whose `last_updated_time` is newer than the cache. The cold path processes every matching PO — expensive at 20k+ rows
- **Bulk pre-fetch pattern for high-volume tenants**: first pass over the result set to collect posids/ticketids/contactids, `mysqli_data_seek($result, 0)` to rewind, bulk-query invoice numbers, ticket types, contacts and contact labels, pre-populate `$_SERVER['values-contacts']`, then run the main loop off the prepared maps — turns tens of thousands of per-row queries into a handful
- **Region access**: `get_accesible_regions_po($dbc)` returns the quoted region list the user may see, from `subtab_config` rows with `tile='purchase_order'` and subtab `po_regions_tab_<REGION>`. Super role gets all regions; `turn_off` adds a region to the exclusion list and `turn_on` removes it, with the query ordered so `turn_off` rows process before `turn_on` overrides; an empty exclusion list means all regions (from the `contacts_region` config); results cache per request in `$_SERVER['po_accessible_regions-'.ROLE]`. POs with an empty region are visible to everyone
- **Label building**: `get_purchase_order_label($dbc, $purchase_order)` accepts either a posid or a full row (passing the row avoids an extra query). Patterns come from `purchase_order_label`, with `_[po_category]` per-type overrides and `purchase_order_label_rma` / `purchase_order_label_backorder` variants (each also per-type); tokens such as the posid, region and date are substituted at runtime
- **Inventory selection is warehouse-filtered**: the add-inventory dropdown and the point-of-sell slider both call `Inventory/retrieve_inventory.php` via Select2, passing the PO header's `warehouseid`. When a warehouse is supplied, the file filters by the `inventory_qty` table if a per-warehouse quantity is present, otherwise by the `inventory.warehouse` column. In `inventory_per_warehouse = 'region'` mode the `inventory.warehouse` filter applies — an item that exists in two warehouses through `inventory_qty` rows will NOT appear unless its primary `inventory.warehouse` matches

## Invoice (`Invoice/`)
- Lifecycle: New → Saved → Completed/Posted → Adjustment → Voided/Archived. Void and credit-note flows are distinct from a plain edit
- Sections render conditionally based on `invoice_fields` (or `invoice_fields_{type}`); `invoice_lines.category` spans service, inventory, misc product, package, staff, Equipment, expense
- **Booking link**: `invoice.bookingid` ties an invoice to a `booking` row (see Sales/Booking)
- PDF template selection config-driven (`invoice_design`); templates query `invoice` and `contacts` directly. `pay_terms` lives on `contacts_cost` not `contacts` — payment terms cascade invoice value → customer default → system default
- DRAFT watermark: Saved invoices show `img/defaults/draft_text.png` at 25% alpha; controlled by `HIDE_DRAFT_WATERMARK` constant (from `$point_of_sell['hide_draft_watermark']`); cached PDFs at `POSAdvanced/download/invoice_{id}.pdf` must be deleted when the setting changes
- `invoice.type` is varchar(20) storing the `config_safe_str()`'d name — NO rename mechanism; renaming in field config breaks all related per-type configs
- **Numbering**: `invoice.type_id` is assigned by a BEFORE INSERT trigger as `MAX(type_id)+1` for the current year (fallback `COALESCE(MINID,'0')` from `invoice_type_id_reset_invoice_type_{type}` config), and also fires on UPDATE when `status` leaves 'Saved'. `type_id` resets per year (a problem for customers wanting continuous numbering). Labels use either `[INVOICEID]` (the PK) or `[TYPE_ID_5]` (zero-padded type_id) depending on customer
- **Renumbering** (when the label uses `[INVOICEID]`): changing `invoice.invoiceid` requires updating the PK and ALL FK tables in the same transaction (`invoice_lines`, `invoice_taxes`, `invoice_pos_history`, `invoice_history`, `invoice_payment`, `invoice_deposits`, `email_communication`, `project_invoice`, `client_project_invoice`, `contacts_donation`) with `SET foreign_key_checks=0`, then reset `AUTO_INCREMENT`. `invoice.reference` can store the original number for historical lookup
- SWO partial invoices use `invoice_lines.deleted=1` to exclude items; excluded items reappear on later invoices
- Auto-archive logic exists in two places (`add_update_invoice.php`, `create_ticket_invoice.php`) — must stay in sync
- **QB export item naming**: the `AUTOSTAX` handling and `qb_item_name` mapping determine how lines and tax appear in the IIF/QB export
- **Deposits**: two-phase Record (money IN) → Apply (reduces owed). WO-specific deposits auto-apply when that WO is invoiced; general/project/estimate deposits apply only on "On Deposit" payment method. Deposits are customer-level (pooled). The `list_deposit_projects_tickets` dropdown selects what a deposit applies to. Config: `ticket_deposit`/`project_deposit`/`invoice_deposit` in `invoice_fields`; key function `get_customer_deposit()`. (`invoice_deposits` table exists but is currently unused for display — do not read it for balances)
- **POSAdvanced** (`POSAdvanced/`): thin wrapper tile — most files set `$current_tile_name = POS_ADVANCE_TILE` then include the Invoice counterpart. The `posadvanced` tile is the entry in `tile_security` (legacy `invoicing`/`pos` tiles are deprecated). Touching a POS invoice may re-cache its PDF. A separate touch-screen POS entry point (`touch_main.php`) drives the touch/kiosk mode
- **AR vs Paid classification**: whether a payment method counts as Accounts Receivable vs Paid is driven by the `payment_type` config (format `T1,T2#*#A1,A2` — the group before `#*#` and after define the two buckets) plus the `invoice_pay_ar` config; the methods "On Account" and "Net X" are always treated as AR. Match the method with an exact `in_array()`, not a substring test
- **PayPal payment status**: `invoice.payment_transaction_status` tracks the PayPal lifecycle (`initiated` → `successful` / `not_completed` / `failed`). The browser return handler (`rm=2`) is primary; the IPN callback is the backup. A sandbox override is guarded by `PAYPAL_GO_LIVE != 1` — never let sandbox mode reach a live customer

## Services (`Services/`)
- 3-level hierarchy: Service Type → Category → Heading (labels via `service_category_label` / `service_heading_label`)
- `services` (main), `rate_billable` (rate card entries), `service_cat_options` (per-category settings)
- Tiered pricing fields: fee, cost, final_retail_price, admin_price, wholesale_price, commercial_price, client_price, purchase_order_price, sales_order_price
- Assigned to tickets via `assign_service.php`; pulled into invoices/quotes/POs via `include_in_*` flags
- Services carry auto-populate fields that push defaults onto the line when a service is selected
- `services.checklist` stores a `#*#`-delimited checklist; `service_history` is the change/audit log; `assign_work` and `set_coa_code` carry work-assignment and chart-of-accounts defaults. The rate-card link joins `rate_billable` on `item_id = serviceid` with `billable = 'services'`

## Timesheet (`Timesheet/`)
- `time_cards` (50+ fields): `staff`, `date`, `total_hrs`, `type_of_time`, `submitted`, `approv` (N=Not Submitted / Y=Approved / P=Payroll / C=Complete), `ticketid`, `ticket_attached_id`
- Pay period automation: Daily, Weekly, Bi-weekly, Monthly, Semi-monthly, Custom. Approval routing via `field_config_supervisor` (Manager/Coordinator, mapped by `staff_list`/`security_level_list`)
- Staff "submit for approval" and admin "submit to payroll" share one code path (`$_POST['submit'] == 'approval'`) — distinguish the caller when behavior must differ. Final approval sets `approv='Y'`; payroll marks entries `P`. Once locked to payroll, previous periods are read-only
- `update_ticket_payable` config gates whether timesheet edits propagate to `ticket_attached`; without it edits are one-directional
- Banked hours in `accrued_time_off` (separates Vaca via `accrued_period NOT IN ('Vaca')`); lock previous periods via `timesheet_searching` / `timesheet_view_previous_periods` subtab permissions
- **`lock_submitted_hours_by_pay_period`** applies a 4-rule lock on a user's OWN timesheet view (once a period is submitted/approved/paid). The lock is mirrored server-side in `Timesheet/time_cards_ajax.php` (never trust the client alone); the `Bypass Payroll Restrictions` subtab is the master override that lets an admin edit locked periods
- **Holidays**: `holidays.colour` (rendered as `border-left: 4px solid` per list row) and `holidays.position_visibility` (CSV of position IDs — only users whose `contacts.position` matches see the record, in Timesheet list and calendar). Tab label via `holidays_tab_label` config (fallback "Stat Holidays"); the "Add Holiday" button gated by the `holidays_add` subtab on the `timesheet` tile. Both colour + position_visibility saved by `Calendar/calendar_ajax_all.php` and `Calendar/field_config_calendar.php`; configurable fields defined in `Timesheet/config.php`
- **Timesheet ↔ Ticket sync**: timesheet row with `ticketid` but no `ticket_attached_id` creates a `ticket_attached` with `sched_id=0`; a fix-up assigns `sched_id` when the ticket is later opened with "Plan Staff"; ticket-side timer check-in/out creates/sums `time_cards`. Known mismatches: rescheduling a stop doesn't update `time_cards.date`; hours edits without the config don't propagate back
- PDF/CSV export is an included file using `ob_clean()` mid-page — its filename/hide variables leak into the parent; its PDF class redefinition is guarded behind the export flag
- **Counted-hours helpers** (`function.php`): a report/accordion header that sums `total_hrs` across all rows over-counts for customers with leave-balance columns (Vac Hrs., Stat Hrs., Break, etc.). Use `get_timesheet_value_config($dbc, $timesheet_type)` (resolves the enabled `time_cards` field config: per-type → tile-wide → `total_hrs` fallback) with `timesheet_counted_hours_sql($dbc, $value_config)` (builds a SQL `IF(...)` that limits `SUM(total_hrs)` to only the `type_of_time` values mapped to enabled columns) instead of `SUM(total_hrs)` directly. Customers with no leave-balance columns get identical results to a blanket sum. Repeated `get_config()` inside these helpers is not N+1

## Inventory (`Inventory/`)
- `inventory` (main), `inventory_change_log` (audit — tens of millions of rows on large tenants), `inventory_qty` (per-bin quantities), `inventory_attr` (per-bin attributes)
- Dashboard uses `setStickyHeader()` with a wrapper-table architecture (separate header table over a scrolling body table) — new columns must be added to BOTH tables or headers misalign. When syncing the header copy, use `.html()` (not `.clone()` — cloning duplicates bound events/attributes); the scroll container is `.standard-body`
- **Per-warehouse inventory** (`inventory_per_warehouse` config) has three modes: `''` = standard (single global qty), `'1'` = per-warehouse, `'region'` = region-tabbed. In per-warehouse/region modes, per-bin `inventory_qty.min_bin` / `max_bin` override the global minimums (with a region-mode fallback chain used by `po_max_bin_alert_check()`). `inventory_change_log` INSERTs must include `warehouse` and `region` (region resolved via `get_field_value()` at write time) — there are multiple writer files, update them all
- `field_config_inventory_attr` drives per-bin attribute config (with `INV_ATTR` constants); the per-bin attribute edit is gated by the default-denied `inventory_attr_edit` subtab
- `field_config_inventory` drives column config; an `ALL_CAT` override applies across all categories
- WIP via request-cached `get_inv_wip_qty()` (`$_SERVER['calc_wip_qty']`); cost = price (or `converted_price` if > 0) + shipping/brokerage/insurance ÷ quantity; `wip_status > 0` forces cost to 0. `validate_inv_change_log()` and `apply_updated_po_currency()` share this formula and must stay in sync
- Change-log replays chronologically to fix old/new values and sync final qty; `inventory_change_log()` must escape `$src_of_change` and check `affected_rows > 0` after flagging a row `used=1`. Most validate calls find nothing — pre-check with a cheap `SELECT ... LIMIT 1` before the UPDATE. Cronjob fix in `auto_status_update.php` runs 1–5AM
- `location_of_change` patterns: `"Purchase Order #[posid]"`, `"[POS_ADVANCE_TILE] #[invoiceid]"`, `"Manually Edited"`, `"Digital Inventory Count"`. A Location Table `strpos` match can false-positive on overlapping location names — compare exact/wrapped values
- The editable-column whitelist in `inventory_ajax.php` must be extended when a new editable column is added. Serialized items link to a parent via `inventory.main_inventoryid` (updating a child recurses to the parent)
- **Bill of Materials**: `inv_bill_of_materials` with a runtime `ensure_inv_bom_columns()` guard; BOM has two save paths and a batch-save. (The `inv_bill_of_materials` CREATE TABLE has pre-existing duplicate/malformed column definitions — this is known; do not flag it as a new issue.) When adding a BOM column, update all three locations (`db_tables.php`, `db_fields.php`, `ensure_inv_bom_columns()`)
- **CSV import**: inventory supports a CSV import path in addition to the AJAX/form save paths
- **Vendor pricing**: `inventory_vendor_pricing` (UNIQUE on `inventoryid`,`vendorid`; columns `avg_cost`, `last_price`, `last_price_currency`, `last_price_converted`, `last_purchase_date`, `total_qty_purchased`) upserted by `update_inventory_vendor_pricing()` in `shared_functions.php` during PO receiving when `type_category=='inventory'` and `vendorid>0`; "Vendor Pricing History" table in `add_inventory.php` gated by a `,Vendor Pricing History,` field-config token
- **Part number / type_id auto-generation**: `generate_default_inv_part_no($dbc, $category, $inventoryid)` uses `inv_default_code_{category}` pattern (e.g. "GBE[ID]") and a per-category (`inventory_type_id_start_{category}`) or system-wide start. TWO save paths: `add_inventory.php` (form POST, BOM category only) and `inventory_ajax.php` (AJAX, all categories)
- Custom fields: `inventory_custom_fields` (definitions), `inventory_custom_field_values` (value stored as `config_safe_str($option)`). Dashboard fires one AJAX call per row — batch/cache to avoid a thundering herd

---

- **Quantity is stored in TWO tables and both must be written**: `inventory.quantity` feeds the dashboard list "Total Qty" column; `inventory_qty.quantity` feeds per-warehouse views, warehouse-filtered queries and the Location Table section (one row per `inventoryid` + warehouse). Updating only `inventory_qty` makes the dashboard show 0; updating only `inventory` makes warehouse views wrong
- **Bin assignment is also dual-write**: `inventory.binid` is the item-level reference, `inventory_qty.binid` is what the dashboard Bin column renders (it joins `inventory_bin` through `inventory_qty`). Setting only `inventory.binid` shows no bin on the dashboard. `inventory_bin`: `id`, `sectionid`, `shelfid`, `name`, `warehouseid`, `deleted` — bins are warehouse-specific, defaults `sectionid=1`, `shelfid=1`
- **Field configuration is accordion-based** (`field_config_inventory`): `tab` (category, or `ALL_CAT`), `accordion` (section name), `order` (1–30 sidebar position), `hide_heading`, `inventory` (comma-separated enabled fields), `deleted`. An `ALL_CAT` row is the fallback and individual category rows override it. Configured from the Inventory gear icon → Fields (`field_config_field.php`), with Tabs / Accordion / Order dropdowns above the field checkboxes
- **Adding a category needs three things**: `field_config_inventory` rows using the lowercase-underscore tab name (e.g. `dead_inventory`), the display name added to the `inventory_tabs` config (`#*#`-delimited), and awareness that `inventory.category` / `inventory_tabs` hold display case while `field_config_inventory.tab` is lowercase-underscore — the code maps between them with `strtolower()` and `preg_replace('/[^a-z]/', '')`
- **One-time import scripts** (browser-run): `$guest_access = true` + `include_once('include.php')` for the connection, `ob_end_clean()` + a plain-text content type for clean output, an execution guard flag in `general_configuration` to prevent re-runs, an `inventory_change_log` INSERT for every quantity/cost change, a backup of affected tables first, and removal of the script and its data files afterwards
- **Excel/CSV import data handling**: convert xlsx with Python `openpyxl` rather than a LibreOffice save-as-CSV — LibreOffice mangles item codes that look like dates (`33-18342`). `openpyxl` returns real datetime objects, so format them explicitly to preserve the displayed value; strip currency symbols, commas and spaces from cost columns before casting to float

## Reports (`Reports/`)
- `Report.php` core class; `field_list.php` master registry (every report MUST be registered there or it will not appear). 300+ report files organized into named tabs (`report_tabs`); tab/config sync lives in `reports_dashboard` / `report_config`; `REPORT_*` constants name the tiles. Each registry entry is a positional array `[file, title, enable_key, security_key, pdf_flag, csv_flag]`. A report is enabled only when it is turned on in BOTH `reports_dashboard` AND `report_config` (the two are synced when a Dashboard Settings save runs). Adding a new tab requires creating the tab's file, registering it in `field_list.php`, and adding it to the `report_tabs` config
- Lifecycle: instantiate → define columns/search fields → set SQL → `initialize_js()` + `display_search_fields()` + `display_table()`. `display_search_fields()` already calls `display_note()` — do NOT call it manually
- Canonical report file pattern: include `require_once('../Reports/Report.php')` (NOT `require` — avoids class-redeclaration fatals when included from `report_tiles_function.php`), construct the Report, register search fields and columns, set SQL, render
- **Column functions**: `make_link`, `time_decimal2time`, `blank_total`, `round`, `callback`, plus a `custom` render column. Currency conversion only applies to `project_scope`. A `function` column formats a single cell value; a `custom` column receives the FULL row and returns HTML (use it when the cell depends on other columns). Wide reports use `set_offsets_columns()` to lay out multiple sub-tables — TCPDF caps a PDF table at ~12 columns, so split wider reports across offset column groups
- **Search field types**: ~80 registered types (contacts, staff, vendor, date/date-range, dropdown, ticket-status, region, classification, service, inventory, project, etc.) — reuse an existing type rather than hand-rolling a filter input. Each type carries its own default; `reorder_search_fields()` controls display order
- `row_function()` runs per row (signature receives the row array + report context); `pre_output_function()` runs before the query (temp tables, aggregation)
- **Data-build gate**: gate building on `isset($_POST['search_email_submit']) || isset($_GET['post_encode'])` — NEVER `!empty($_POST)` (POST is always populated because it's merged with `$_GET`). Note the embedded-tile guard uses `!= '0'` (`if(!isset($search_options) || $search_options != '0')`)
- **Export machinery — two paths**: `set_report_sql()` MUST run for the PDF/CSV export path too. The JS export uses `new FormData()` which excludes submit buttons, so `search_email_submit` is not set during export; if `$this->sql` is unset on the export path the progress bar hangs at "Initializing". There is a separate `progress_bar` (export) vs `build_progress` (data build) tracking. The tiles-wrapper override handles reports embedded in a tile. `next_buttons.php` is dead code — do not extend it. When a report is embedded in a tile, the Report class's own `initialize_js()` re-defines `printPDF`/`printCSV` and OVERRIDES the tiles-wrapper versions — if export breaks only inside a tile, this override (and re-defining a class after output) is the usual cause
- **Export column dialog**: the "choose columns" export dialog is `#dialog-column-options` submitting `output_columns[]`; the chosen columns filter both headers and data via a key→label `colMap`. The export progress row stores the DB `CONNECTION_ID()` so a stuck export can be identified/killed
- **`COUNT(*)` pagination caveat**: the row-count query used for pagination wraps the full SQL — any `ORDER BY` and derived/computed columns still execute inside the count, so a heavy report is slow even to count. Keep derived columns out of the base SQL where possible, or the count query becomes as expensive as the data query
- **Report-specific SQL optimization**: reports run large aggregates — apply the sargable-date/`FIND_IN_SET`/split-`OR`-`UNION` rules aggressively; batch per-row lookups in `row_function()` via a `pre_output_function()` prefetch
- All tile folders must have a writable `download/` subfolder owned by `www-data` (Report writes PDF/CSV there)
- Drive-time / geofence-time / compensation / callback columns follow a shared parameter pattern (a config-driven callback receives the row and returns the computed value)
- When embedded as a tile sub-tab, the parent sets `$search_options = '0'` and pre-populates the filter — wrap the parent-tile search field with `if(!isset($search_options) || $search_options != '0')`

- **Callback / clickable columns must populate `$data[]` outside the display branch.** Columns that render HTML through a callback (e.g. a currency value that is also a drill-down link) branch on `$this->search_items['printpdf']` / `['printcsv']`: on screen the full HTML is appended, for PDF the same string is appended through `strip_tags()`, and for CSV/JSON nothing is written to the HTML at all. If `$data[]` is assigned inside that if/else, CSV and JSON cells come out blank — assign it unconditionally. Build the raw numeric value with `trim(str_replace(array('$', ','), '', strip_tags(html_entity_decode($callback_response, ENT_QUOTES))))` so the export carries a number, not formatted currency

## Security (`Security/`)
- `security_level_names` (`identifier`, `label`, `active`, `custom_order`); custom levels use `FFMCUST_` prefix; `super` bypasses field permissions
- Field-permission keys: `{tile}_fields_hidden_{level}` / `{tile}_fields_readonly_{level}` (ticket adds a `{ticket_type}` segment)
- **Multi-role resolution differs by permission kind:**
  - **Tile access** across multiple roles is **most-permissive** — if ANY role grants the tile, the user sees it
  - **Field permissions** across multiple roles resolve **least-restrictive** via `array_intersect()` — a field is hidden only if ALL roles hide it
- Field-level enforcement is **client-side only** (disabled attribute + display:none); AJAX save handlers store whatever keys are sent — known architectural limitation

### is_login.php vs checkAuthorised() — Two Separate Authorization Levels
`is_login.php` provides **session-level auth only** — it confirms a valid login session and redirects to login if not. It does NOT enforce tile-level authorization. `checkAuthorised('tile_name')` enforces **tile-level access** — without it, any authenticated user (regardless of security level or tile permissions) can reach the endpoint. New AJAX endpoints and standalone files must call `checkAuthorised()` immediately after `include_once('../include.php')`. A file that includes only `is_login.php` without `checkAuthorised()` is not tile-authorized. (The established exception remains slider/iframe files loaded via `overlayIFrameSlider`, which rely on the parent page's auth.)

### Region / Free-Text Filter Values Need Allowlist Validation
When an AJAX endpoint accepts a region (or similar free-text grouping) string as a POST/GET parameter, validate it against the system's configured values before using it in a query. Escaping prevents SQL *syntax* breakage but does NOT prevent a valid-syntax query that leaks data from another region — the allowlist is the authorization control, escaping is still required alongside it:
```php
$allowed_regions = get_all_regions($dbc);
if($region != '' && safe_in_array($region, $allowed_regions)) { /* safe to use $region */ }
```

### get_security($dbc, $tile) — Permission Summary Helper
`get_security($dbc, $tile)` (in `shared_functions.php`) returns an associative array summarizing the current user's privileges on a tile (derived from `get_privileges()`). Use it to gate an edit-only UI action instead of re-parsing privilege strings inline. Keys (all `0`/`1` unless noted): `dashboard`, `visible`, `add`, `archive`, `encrypted`, `inactive`, `edit`, `search` (`1`/`2`/`0`), `config`, `approval`. Usage: `if(get_security($dbc, 'scrum')['edit'] > 0) { ... }`. Fetch it once at the top of a file and reuse it — do not call per row in a loop.

### MATCH_CONTACTS — tickets vs inventory Column Scope
`MATCH_CONTACTS` is a CSV of `businessid` values for multi-tenant isolation. `$match_business` is built as `AND tickets.businessid IN (MATCH_CONTACTS)` and is only valid in queries that JOIN `tickets`. In queries directly against `inventory` (no `tickets` join), `$match_business` references an unknown column and makes `mysqli_query()` return `false`, silently zeroing every count/result. Use a separate filter on `inventory.business` there:
```php
$match_business_inventory = " AND (`inventory`.`business` IN (".MATCH_CONTACTS.") OR `inventory`.`business` = '' OR `inventory`.`business` IS NULL)";
```
Use `$match_business` only with a `tickets` join; use `$match_business_inventory` for inventory-only queries. The NULL/empty fallback keeps unassigned items visible.
- Subtab permissions: `subtab_config` table; `check_subtab_persmission()` → `load_check_subtab_persmission()`; no row generally = allowed. Specific subtabs are hardcoded to default-DENIED — currently: `po_settings`, `change_contact_username`, `document_settings_project_settings`, `ticket_rate_fees`, `update_vendor`, `inventory_attr_edit`. `status` format `*turn_on*#*{date}` / `*turn_off*#*{date}`
- **`get_privileges()` default**: returns `'*'` (full/visible) when no privilege row exists — absence of a row means allowed, not denied. Guard accordingly when adding a new privilege that must default OFF (insert an explicit deny row rather than relying on absence)
- **Multi-role membership**: a contact's roles are a CSV in `contacts.role`. Field-permission intersection across roles is implemented by appending a sentinel before `array_intersect()` so a single-role user still intersects correctly — preserve that sentinel when touching the resolution logic. Related config tables: `security_privileges`, `quickactionicon_config`, `field_config_project_admin`
- **Profile-slider auth (`contacts_inbox`)**: the contact profile slider authorizes via `src_tile` — when opened from tickets (`src_tile=tickets`) it checks the `edit_contacts`/`view_contacts` subtab, otherwise it falls back to `checkAuthorised()`. A denial is a JS redirect to `home.php` (NOT a PHP error), which makes the slider appear to blink open then close — recognize this symptom as an authorization failure, not a rendering bug

---

## Calendar (`Calendar/`)
- `ticket_monthly_card.php` renders inside a loop — any new query MUST use batch prefetch or it causes N+1
- **Block type system**: calendar blocks carry a `data-blocktype` (`equipment`, `staff`, `dispatch_staff`, `team`, `client`) that routes drag-and-drop and rendering. Equipment/staff assignment tables: `equipment_assignment`, `equipment_assignment_staff`, `teams_staff` (staff→equipment lookups go through these). The `schedule_unbooked` handler manages the two-block (booked/unbooked) case
- Drag-and-drop equipment assignment has two code paths (dispatch vs staff/WO calendar); `$overlay_slider` routes card clicks (Program Sheet vs Registration); `TOP_FOLDER_NAME` unreliable when embedded
- Event calendar config: `event_calendar_fields` / `event_calendar_signup_fields` (Site / Site Only / Auto Calendar Invite options). Site name may be an encrypted value — fall back to the decrypted value; sites are batch-cached in `$_SERVER['__batch_sites']`
- **Sidebar filters** (Staff / Teams / Region): user selections stored in `user_settings` (`appt_calendar_staff`, `appt_calendar_teams`, `appt_calendar_regions` — CSV); saved via `Calendar/calendar_ajax_all.php` (`fill=selected_staff` / `fill=selected_contacts`). The Teams panel queries the `teams` table filtered by the user's allowed regions (`$region_query` built from `contacts.region`); each team block carries `data-teamid` and `data-contactids`
- **Mobile card view**: `ticket_calendar_mobile_card_view` config (Calendar Gear → Calendar Options); when enabled and `$_GET['tile_name']=='membership_portal'`, programs render as cards on the mobile day view (`.mobile-card-view` class in `calendars_mobile.php`)
- **Classification-as-location grouping**: for tenants that do not use regions, classifications can act as a location grouping (a "Manor"-style grouping) on the calendar; visibility is config-gated via `config_safe_str()` subtab keys

## Dispatch / Optimize (`Optimize/`)
- `assign_ticket.php` runs an equipment-sync UPDATE on each non-support search; the subquery must scope with an INNER JOIN to `ticket_schedule` (deleted=0, empty/NULL equipmentid, to_do_date within 30 days) — a full-table LEFT JOIN caused multi-second blocking. Support searches bypass the sync

## Sales / Booking (`Sales/`, `Booking/`)
- `sales_lead_status` (CSV) does NOT include Won/Lost (stored in `lead_status_won`/`lead_status_lost`); Unassigned column must show only `status IN ('Unassigned','')`, not `NOT IN (configured)`; the Unassigned re-stamp UPDATE runs on every page load (perf concern, no history)
- Quick-add dropdowns use `data-add`: `1` shows select2 "Add New" (if permitted), `0` hides it; gated by `check_subtab_persmission(..., config_safe_str(CATEGORY).'_profile_add')`
- **Booking**: `booking.salesid` links a booking to a sales lead, `booking.serviceid` to a service; a resulting invoice references it via `invoice.bookingid`
- **Sales-lead linkage** also flows through `tickets.salesid` and `invoice.salesid` — a ticket or invoice can be tied back to the originating lead
- **Sales tab visibility is dual-gated**: a Sales sub-tab shows only when it is enabled in BOTH `field_config.sales` AND the `sales_section_tabs` config, and the tab file is registered in `field_list.php`. Missing any one silently hides the tab

## FormBuilder (`FormBuilder/`)
- 40+ field types. SELECT = contact picker (AJAX Select2); SELECT_CUS = static dropdown. TEXTBOXREF is stored as TEXTBOX. CONTACTINFO populates from an existing contact; NEWCONTACTS creates one on submission — both query `field_config_contacts` with `subtab='**no_subtab**'`
- `CONTACTINFO.contact_target` selects the source: `SELF`, `SYNCED`, `SYNCED_SYNCED_CONTACTS`, `ALL_CONTACTS`
- Field rendering in `generate_form_contents_field.php` (ACCORDION/CONTACTINFO/NEWCONTACTS pre-switch, rest in main switch). POST key: field `field_123` → `field_field_123`; contact pickers submit as nested arrays keyed by `field_id`. TICKET_ defaults populate from a WO when `$_GET['ticketid'] > 0` but do NOT pre-select a SELECT contact picker
- Checkbox/dropdown/`source_conditions` are stored in a delimited format; math fields use `user_form_field_math_calc`; cross-field references use `[[input_field_N]]` placeholders (backed up/restored around edits)
- Auto-save fires per field change → `form_ajax.php?fill=save_field` (creates `pdf_id` on first save). Storage: `user_form_pdf`, `user_form_data` (encrypted values), `user_form_field_value` (auto-save intermediate). "Allow Revisions" per-field via `user_form_field_attr.allow_revisions` (revision text in `edit_text_revisions` / `revision_value`). System config in `field_config_user_forms`. `edit_form_fields.php`/`edit_form_field_details.php` are shared by ALL form-builder tiles — scope via `$_GET['from_tile']`

## Contacts (`Contacts/`)
- `contacts.tile_name`: 'contacts', 'vendors', or 'staff' (shared table). Tab configs: `contacts_tabs`, `vendors_tabs`, `contacts_vendors_synced_tabs`
- Encrypted name columns (`first_name`, `last_name`) cannot be searched/sorted in SQL — `sort_contacts_query()` computes `full_name` and list endpoints filter the search term in PHP AFTER loading (no SQL text filter). Calling `get_contact($id, 'full_name')` after `sort_contacts_query()` is redundant; the function is used across many files — keep the signature backward-compatible
- Preferred name vs legal name are distinct fields — respect which one a given display context calls for
- Tenant isolation via `MATCH_CONTACTS` + `$query_match_program`; `contacts_sync` holds bidirectional synced relationships; `site_name` syncs across synced contacts. New contacts are created in a non-active `deleted` state until a detail is entered/activated (follow the feature's existing flag value)
- **Export classification merging**: `get_contact_export_data()` accepts a `$classification` argument — a specific classification merges fields from `contacts_fields_classification_{category}_{classification}`; no classification merges ALL classification configs for the category (LIKE query). `Contacts/list_common.php` JS reads the active classification from the sidebar (`li.active[data-classification]`) and passes it to the AJAX + export form
- **Contact picker contract (`initContactItems()`)**: contact-picker Select2 fields are driven by data attributes — `data-sync`, `data-category`, `data-classification`, `data-restriction`, `data-project`, `data-exclude` — and resolve options through the `list_of_contacts` endpoint. `sync_type` levels control which synced relationships are included. Reuse this rather than building a bespoke contact dropdown. `data-category` is sent to `list_of_contacts` as `search_cat` and split on `,` — it expects PLAIN comma-separated names (`Location,Vendor`). Some configs store values underscore-wrapped (e.g. `ship_to_types_*` stores `_Location_,_Vendor_` for a legacy SQL builder); normalize before emitting into `data-category`: `trim(str_replace('_,_', ',', get_config($dbc, 'ship_to_types_'.config_safe_str($type))), '_')`. Also render `data-sync` (a contact id, to scope results to that customer's synced contacts) into the HTML at page load when the record already has a customer — assigning it only via a customer-dropdown `onchange` leaves the FIRST render of an existing record unscoped
- **New-contact placeholder**: a blank new contact is inserted with `deleted=2` and only activated once a real detail is entered; activation is decided by a 9-field name/detail check, and the history row is written only on the state transition (not on the placeholder insert). This is the Contacts-specific instance of the general placeholder-row pattern — follow this flag value for contacts
- **List cache**: contact list endpoints read from a per-tenant cache file (decrypted names sorted in PHP, since name columns are encrypted); when adding a field to the list output, invalidate/rebuild the cache or stale rows appear
- **Classification-summary drill-down** must batch `sort_contacts_query()` — collect the contact ids first and run a single query, never call the sort per row

- **Two contact-dropdown initialization patterns exist and are not interchangeable**: `init_select2_contacts` is the global pattern used on non-ticket pages, while `contact_select2` is the pattern used inside the ticket editing context. They differ in how options are fetched and re-initialized after AJAX, so a dropdown copied from a ticket page into a global page (or the reverse) silently fails to populate. Match the pattern already used by the page you are editing rather than importing the other one

## Email (`email.php`)
- `send_email()` is the core SwiftMailer send. From-address: empty string → `EMAIL_USER` as envelope sender; array → provided address as Reply-To. `software_send_options` config (`#*#`-delimited `Name|*|email`) and `staff_email_field` config control routing. No email-signature field — `stored_signature` is for drawn/physical signatures only
- **Email groups / mass send**: `get_email_group_emails()` resolves a group's recipient list; a group's `contact_category` is stored as `#*#`-delimited OR-blocks; a Volunteers group keys off `allow_volunteer`. The `newsletter_email_groups_contacts` table holds the per-contact membership synced from the resolved group. Recipient suppression has three distinct concepts — Exclusion (per-send), Unsubscribe (permanent opt-out), and Agreement (must have agreed) — do not conflate them

- `get_email_group_emails($dbc, $groupid, $return_type = 'emails', $options = array())` — `$return_type` selects `count`, `emails`, `contactid`, `contactid_emails`, `contact_details` or `criteria` (criteria labels for display). Options: `allow_no_emails` (include contacts with no email), `skip_exclusion` (do not filter excluded contacts out of the count), plus `rowsPerPage` / `pageNum` / `offset` for pagination. Criteria blocks in `contact_category` are OR'd against each other and AND'd within a block; manually added `contactid` entries always join the result regardless of criteria; excluded contacts are removed with a SQL `NOT IN` for counts and shown struck through in the display
- `email_groups.category` controls which CRM subtab lists the group: `Both` (default) appears in both, `Newsletter` only in the newsletter dropdown, `Survey` only in the surveys dropdown (the tabs filter with `category IN ('Newsletter','Both')` / `IN ('Survey','Both')`). Groups sort by context (project-specific, then business-specific, then general), then the drag-and-drop `sort_order`, then group name
- **CRM surveys**: with `anonymous = 1` the form hides the whole contact-information block (first/last name, email, stay-anonymous checkbox) and posts a hidden anonymous flag instead of identity fields. On a public-link submission by a non-logged-in user, the entered email is matched against the encrypted `contacts.email_address` and `contacts.office_email` and the submission is linked to the existing contact instead of creating a duplicate — only when there is no session, an email was given, and the survey is not anonymous. When a department is set, the sender resolves to the first active staff member in that department with an `admin` role, falling back to `lead`, then `manager`, then the default sender address

## Cronjobs (`cronjobs/`)
- Bootstrap via relative path; set `$guest_access = true` before include. No `$_SESSION`/`$_GET`/`$_POST`; session-dependent constants are empty — read config directly with `get_config()`. Set session/MySQL session values manually if triggers/history need them
- **Mass email** (`cronjobs/email_groups.php`): single entry point for all mass email types, sends via the mDirector OAuth API (`newsletter_consumer_key`/`newsletter_consumer_secret`). `newsletter.newsletter_email_group` → `email_groups.groupid` → `email_groups.list_id` (mDirector list). Flow: sync contacts to list → create campaign via OAuth → send. `sent`: 0=Draft, 1=Sent, 2=Scheduled, 3=Error. Diagnose `sent=3` with `envId=0` = campaign creation failed; `envId>0` = send failed. Manual resend: set `sent=2`, ensure `scheduled_date` within 24h, run the cronjob
- `auto_archive` and `auto_status_update.php` cronjob passes run in the early-AM window

---

## Global Search (`search.php`)
- Dual-mode: AJAX (10 results, one category via `$_GET['category']`, `ob_clean()`) and non-AJAX advanced (500 results, all categories with counts). Tenant isolation via `MATCH_CONTACTS` + `$query_match_program`; `[CACHE_QUERY]` handled by `sort_contacts_query()`. Perf hotspots: ticket N+1, repeated contact-sort calls, sales JOIN full scan

## Geo-Location Mobile App (`geo-location-app/`)
- Monolithic JSON REST API for the Flutter app (JWT auth, single action switch). Has LOCAL copies of `get_config()`, `get_user_settings()`, `get_security_levels()` that shadow the shared versions. Any JSON shape change needs a coordinated mobile release. `store_gps()` is shared across callers. Depends on `php8_compatibility_fixes.php` being included by `shared_functions.php`

## Equipment (`Equipment/`)
- Equipment "service schedules" and "rental schedules" are filtered work-order lists, NOT independent scheduling engines — they query tickets/`ticket_schedule` with equipment/type filters

## QB / Sage Export
- Invoice (`invoice_ajax.php`), PO (`purchase_order_ajax_all.php`), Contacts (`contacts_ajax.php`) each expose `qb_export` (IIF) / CSV / Sage actions, gated by the `allow_qb_export` subtab. `invoice.exported`: 0=needs export, 1=exported, 2=voided after export. Filters exclude deleted/Saved/Archived. Tax allocation iterates `field_config_tax_details` for the invoice's rate and splits total tax proportionally. Item naming via `AUTOSTAX` / `qb_item_name`

## NewsBoard + Scheduled Email (`NewsBoard/`)
- Local posts use `$dbc`; Softwarewide posts use `$dbc_htg` (by `newsboard_type`). Opening the editor with empty id inserts a blank row and redirects — orphan rows exist by design; `expiry_date` defaults to `2030-12-31`. Individual boards/tabs are gated by `check_subtab_persmission($dbc, 'newsboard', $level, $tab_name)` — an empty `tab_name` means the board is visible to all users
- Scheduled sends use `sent`: 0=Draft, 1=Sent, 2=Scheduled, 3=Error. `scheduled_date` refreshed on Send (CASE WHEN snaps past dates to NOW(), preserves future); `cronjobs/email_groups.php` processes `sent=2`, auto-retries `sent=3` after 1 hour; `$_GET['cron_mode']=1` uses direct in-loop processing instead of per-contact RollingCurl HTTP. Same pattern for newsletters, surveys, digital forms, evites

## Intake (`Intake/`)
- Public forms submittable without login. `intake_forms` is the config wrapper (links `user_forms`); `intake` holds submissions. Access code in the URL: `/Intake/add_form.php?formid=<id>&access_code=<code>`. `require_login` (default 1) → set 0 for anonymous access. Anonymous submissions have empty `$_SESSION['contactid']` — guard auto-population
- **Classification-based access**: `intake_forms.classification` (varchar 500). When set, visibility is gated by `subtab_config` permissions for the `intake` tile using `config_safe_str($classification)` as the subtab key; the Security tile exposes intake subtab permissions and `Intake/config.php` filters `$form_types` by the user's roles. No row = access granted; empty classification = visible to all

## Galleries (`Galleries/`)
- `galleries`, `gallery_categories`, `gallery_media`. Featured gallery slideshow; public page `featured_gallery.php` (no login). Uploads limited to `.jpg,.jpeg,.png,.pdf`. A gallery can be exported to a PowerPoint (`.pptx`) slideshow

## Customer Portal / Support (`Support/`)
- Customer-facing portal lives in `Support/` (entry `customer_support.php`); `Website/` is the public marketing CMS. Requires config in TWO DBs: main (`$dbc`) and support (`$dbc_support`); `cust_support_tab_list` must exist in BOTH (intersection logic) or the page renders blank. Portal-created tickets/quotes inserted `deleted=3`. Invoice creation routes via `review_invoice=customer` through `Invoice/config.php`. Shipping/tracking integrations (FedEx, EasyPost) are surfaced here — FedEx uses an OAuth token flow (fetch/cache a bearer token, then call the rate/track endpoints); EasyPost uses its API key with shipment/rate objects. Wrap both in try/catch and never let a carrier API failure crash the portal page

## Gantt Chart
- All Gantt files query both `to_do_date` and `to_do_end_date`; bar end uses `+1 day`. Transport-log rows: `ticket_schedule.deleted=20`, grouped by `IFNULL(NULLIF(sched_id,0), id)`. Type filter checkboxes default checked, use `IN (whitelist)`. `$label` may contain HTML — use `strip_tags()` for `title=""`. `date_type_label` codes: `DS`/`DA`/`EA`/`OD` denote which date pair a bar is drawn from

## Geofence Alerts
- `fire_geofence_alerts()` evaluates geofence entry/exit and dispatches alerts; drive-time and geofence-time report columns read from the same GPS/geofence data

## HR / Safety
- `hr_attendance.fieldlevelriskid` stores the associated `pdf_id`. A `today_date` trigger exists on some tables in PRODUCTION only — do not rely on it locally; include the date explicitly in the INSERT. Some HR/Safety reports are built from a UNION of multiple sources; guard against duplicate inserts using a `$GLOBALS` flag where the same include runs twice

## Activity / Payments
- `ticket_attached.payment_paid` / `paypal_id` record activity-level payment state (e.g. PayPal transactions tied to a line item)

## CRM Alerts (`CRM/`)
- Automated notifications triggered by cron jobs checking conditions (expired certifications, unsubmitted timesheets, upcoming birthdays). Files: `CRM/crm_alerts.php` (dashboard), `CRM/crm_alert_config.php` (per-type config UI), `cronjobs/crm_alerts.php` (evaluates triggers, creates records), `CRM/crm_ajax_all.php` (AJAX actions). Tables: `field_config_all_alerts` (type definitions/config), `all_alerts_history` (instances: `alert_type`, `contactid`, `status` Active/Dismissed/Resolved, `created_date`, `triggered_by`)
- Adding an alert type: add a row to `field_config_all_alerts`; add trigger logic to `cronjobs/crm_alerts.php`; add config UI in `crm_alert_config.php` if it needs settings; the security permission auto-registers via the existing `register_security_privileges()` pattern

## MySQL Login Functions (ff_encrypt / ff_decrypt)
Some customer databases use MySQL stored functions `ff_encrypt()` / `ff_decrypt()` for password comparison in the login query. If missing (e.g. a freshly imported database), login silently fails with "invalid credentials" and no error. Diagnose with `SHOW FUNCTION STATUS WHERE Db='database_name' AND Name LIKE 'ff_%';` and restore by copying the definitions (`SHOW CREATE FUNCTION ff_encrypt;`) from a working database.

## Cross-Cutting Behaviors & Traps
- **`config_safe_str()` read/write symmetry** — reader must apply it too or the lookup silently misses
- **`strpos()` on comma-separated config values false-positives** on overlapping substrings — use `FIND_IN_SET` or wrap both sides in commas
- **Comma-wrapped config is never `empty()`** — test the raw `get_config()` value before wrapping
- **Double-quoted SQL with `'.$var.'`** does not interpolate — use `"...".$var."..."`
- **Wrong config source returns empty silently** — `field_config` tables and `general_configuration` are different stores; `get_field_config($dbc,'tickets')` ≠ `get_config($dbc,'ticket_fields')`
- **Scope field label aliasing direction matters** — production and feature branches can alias opposite directions; default labels must match what the environment currently displays, and scope column whitelists must agree across the heading/detail/footer/line files or the table layout breaks
- **RDS `AUTO_INCREMENT` reads stale** — after `ALTER TABLE ... AUTO_INCREMENT = N` on RDS, `information_schema.TABLES.AUTO_INCREMENT` may show the old value; run `ANALYZE TABLE tablename` to refresh the metadata (the actual auto_increment is applied correctly regardless)
- **CLI vs web DB selection** — `db_connect.php` selects the DB differently under CLI; confirm the target customer DB before trusting CLI query results

## Customer-Specific Behaviors (config-driven, durable)
- **Can-Seed**: PO Design 6, Milestone Summary disabled
- **Astoria**: manual fee entry (editable rate-card flag), Miscellaneous invoice section
- **General Body**: non-CAD system currency (NOK) so report monetary values convert (only `project_scope` carries currency metadata); very large audit tables (35M+ `inventory_change_log`)
- **SES**: dispatch / drive-time / geofence reporting heavy
- **WTS**: logistics / shipping workflows, work-order CSV export
