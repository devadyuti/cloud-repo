---
inclusion: manual
---
# ExampleApp Architecture Patterns

Load when adding a feature, endpoint, configuration option or tile-level behaviour, or when you need to know how the platform is wired (bootstrap, config store, helper functions, session, caching). Per-tile internals are in `module-knowledge.md`.

---

## Core Conventions

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

AJAX patterns for new endpoints: see `javascript-standards.md`.

---

## Reports Embedded in Tiles
When a report is embedded inside a tile as a sub-tab, the parent tile case sets `$search_options = '0'` and pre-populates the filter POST variable. In this scenario, the parent-tile search field must NOT display (the user is already in that context). Wrap it:
```php
if(!isset($search_options) || $search_options != '0') {
    $search_fields[]['project'] = array(...);
}
```

---

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
