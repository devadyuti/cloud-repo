---
inclusion: manual
---

# Platform Configuration & Audit Infrastructure (Reference Only)

Durable ExampleApp architecture knowledge for the configuration, flagging,
tax, theming, and API subsystems. Not needed to review the sample contact
list app, but preserved here for fidelity with the full standards doc and
for use on tickets that touch these subsystems in the real product.

## Configuration & Audit Infrastructure
- **`general_configuration`** — key/value store; read with `get_config()`,
  write with `set_config()`. The trap: `field_config` tables and
  `general_configuration` are different stores
  (`get_field_config($dbc,'tickets')` ≠ `get_config($dbc,'ticket_fields')`);
  the wrong source returns empty silently.
- **`field_config`** — single-row table with one column per tile
  (`tickets`, `purchase_order`, `inventory`, `time_cards`, …); each column
  stores a comma-separated list of enabled features/fields. Read via
  `get_field_config($dbc, 'column')` which returns the list comma-wrapped
  (`,value,`) for `strpos` matching and caches in `$_SERVER['field_config']`
  after first read.
- **`all_config_history`** — audit of all configuration changes:
  `table_name`, `config_name`, `prior_value`, `new_value`, `src_script`,
  `created_by`, `created_date`, `ip_address`.

## Multi-Flag System
- `item_flags` — central flag storage (`item_flag_id`,
  `item_flag_tile_id`, `record_id`, `flag_colour`, `flag_label`,
  `flag_start`, `flag_end`, `flag_user`, `flagged_by`, `flagged_date`,
  `deleted`).
- `item_flag_tiles` — maps tile names to integer IDs.
- `flag_display_inc.php` — shared display include. Set `$flag_tile` and
  `$flag_record_id` before including; it sets exactly four variables:
  `$flag_styling`, `$flag_label`, `$flag_badge`, `$flag_count`.
- `get_item_flags($dbc, $tile, $record_id, $active_only)` /
  `get_item_flags_batch($dbc, $tile, $record_ids)` — use the batch version
  on dashboards to avoid N+1.
- `quick_action_flags.php` — handles all flag writes; writes ONLY to
  `item_flags`. Legacy `flag_colour`/`flag_label`/`flag_start`/`flag_end`
  columns still exist on tables but are NOT read for display.

## Tax Rate System
- `field_config_tax_rates` — `id`, `tax_name`, `tax_rate` (percent),
  `contactid` (0 = all vendors, >0 = vendor-specific), `tax_code`,
  `tax_registration`, `gl_code`, `exempt`, `editable`, `deleted`.
- `field_config_tax_details` — `tax_id` (PK), `rate_id` (FK →
  `field_config_tax_rates.id`), `detail_name`, `tax_rate` (component
  percent), `detail_registered`, `gl_code`, `deleted`.
- **Apply-to-cost**: `field_config_tax_details.apply_to_cost_po_types` and
  `purchase_orders_product.apply_to_cost_amount` — calculated during PO
  receiving.

## Configurable Time-Off Column System
- `get_time_off_types($dbc)` — returns type definitions from the
  `time_off_types` JSON config; each type has `id`, `label`, `input_mode`
  (`hours`|`fraction`), `behavior` (`accrue_reduce`|`manual`|`record_only`),
  `deleted`.
- Balances tracked in `accrued_time_off`; columns appear on the timesheet
  via field config keys `timeoff_{id}` (balance) and `timeoff_{id}_used`
  (entry).

## Software Theme System
- Theme CSS: `css/style_[theme_key].css`; background images under
  `img/[theme_key]_theme/`.
- A new theme must be registered in THREE files: `header.php`,
  `login_page_style.php`, `Settings/style_config.php`.
- Selection stored per-user in `contacts.software_styler_choice`,
  software-wide in `general_configuration.software_default_theme`, and
  per-security-level in `field_config_security_level_theme.theme`.

## API System (`Api/`)
- JSON REST endpoints served from `Api/data.php` (and siblings). Calls are
  logged/tracked in `api_calls` table(s). Any change to a response shape is
  a public contract change — coordinate with consumers before altering keys
  or types.
- Config/audit tables: `api_calls`, `api_call_options`, `api_call_values`,
  `api_call_history`.

## Settings & Navigation (`Settings/`)
- Central settings tabs, logo uploads, and the global action slider live
  under `Settings/`. The global quick-action slider's contents are driven
  by `quickactionicon_config`.
- **Dashboard default selection** (`home.php`): `tile_dashboards` holds
  `dashboard_id`, `name`, `tile_sort`, `default_levels`, `assigned_users`,
  `restrict_levels`, `deleted`; `contacts_tile_sort.default_dashboard`
  holds the user's own choice. Priority: (1) an explicit `?dashboard_id=X`,
  (2) the personal default, (3) a role match in `default_levels`.
