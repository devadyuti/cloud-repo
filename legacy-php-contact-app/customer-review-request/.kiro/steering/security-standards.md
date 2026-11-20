---
inclusion: manual
---
# Security Standards

Load when the work involves authorization, permissions, input validation, SQL construction from user input, file uploads, sessions, encryption or any new endpoint. Note: XSS/output escaping analysis is skipped in QA reviews — escaping is handled at render time per the established codebase approach.

---

## SQL Injection Prevention
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

---

## Core Security Rules

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

## Security Module Internals (`Security/`)
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
