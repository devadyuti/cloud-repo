---
inclusion: manual
---

# Codebase Knowledge — Module Internals (Reference Only)

How the full ExampleApp software actually works, organized by tile/system.
Durable architecture — table relationships, function behaviors, config
patterns, and recurring traps that apply across tickets in the real
product. Not needed to review the sample contact list app; invoke with
`#module-architecture` when working on a ticket that touches one of these
tiles.

## Platform Architecture
- No framework, no Composer autoloading, no MVC, no modern JS bundler.
  Entry points are standalone `.php` files bootstrapped by `include.php`.
- Tile-based: each top-level directory is one feature area. AJAX routes
  through centralized handlers (`ajax_all.php` and per-tile `*_ajax.php`)
  via `$_GET['fill']` / `$_GET['action']`.
- Multi-tenant: each customer has its own database/instance. The same tile
  behaves differently per customer because labels, statuses, and enabled
  features are config-driven.
- `run_cronjobs()` in `include.php` executes synchronously on every page
  load. Login/auth flow is centralized in `is_login.php`.

### Core Helper Functions
- `get_config($dbc, 'name')` / `set_config($dbc, 'key', 'value')` /
  `load_config($dbc, [...])` (hardcoded defaults, final fallback `''`).
- `get_contact($dbc, $contactid, 'field')` — contact data lookup.
- `get_field_value($dbc, ...)` — single field value lookup (returns `null`
  on miss, unlike `get_config()`/`load_config()`).
- `config_safe_str($string)` — normalizes a value for use as a config key
  suffix (read/write must both apply it).
- `file_safe_str($filename, $folder)` — safe + unique uploaded file names.
- `tile_visible($dbc, $tile_name)` — tile visibility check.
- `IS_AJAX` constant: `'AJAX'` or `'NO'`.

### get_contact() Per-Request Cache
- Caches in `$_SERVER['values-contacts'][$field_name]['contactid-'.$contactid]`.
  Only used when `$dbc === $_SERVER['DBC']`. For dashboards/lists/exports,
  pre-populate the cache with one bulk query before the render loop.

## Ticket / Programs / Work Orders (`Ticket/`)
- Core table `tickets` (100+ fields). Related: `ticket_attached`,
  `ticket_schedule`, `ticket_comment`, `ticket_checklist`,
  `ticket_attached_membership`.
- Organized by ticket types (tabs) via `ticket_tabs` config. Per-type field
  config stored as `ticket_fields_{type}`.
- Staff has TWO views: Staff accordion (`sched_id=0`) and Plan/Schedule
  view (schedule-based staff, timepicker inputs).
- Billing hours fallback: `IFNULL(NULLIF(bill,0), hours)`.
- `alert_users()` sends registration/confirmation email + ICS.

## Estimate (`Estimate/`)
- `estimate`, `estimate_scope`, `estimate_scope_heading`. Scope monetary
  fields are `est_retail` / `retail` — there is NO `est_total` / `total`
  column on scope.
- Two history tables: `estimates_history` (main log) vs `estimate_history`
  (status audit, different `updated_by` semantics).

## Project (`Project/`)
- `projects`, `project_scope`, `project_scope_heading`, `project_path`,
  `project_billing`. Cost semantics: `project_scope.cost` = planned cost
  (never overwritten by PO actuals), `actual_cost` = actual from PO
  receiving, `price` = sell price.

## Purchase Order (`PurchaseOrder/`)
- `purchase_orders` (header), `purchase_orders_product` (line items).
  Statuses: RFQ, Estimated, Real-Time, Pending, Pending Approval,
  Receiving, Paying, Processed - Not Paid, Paid, Back Ordered, Completed.
- Two payment-term systems coexist: legacy `po_payment_terms` config AND
  `ratecard_payment_terms` table.

## Invoice (`Invoice/`)
- Lifecycle: New → Saved → Completed/Posted → Adjustment →
  Voided/Archived. `invoice.bookingid` ties an invoice to a `booking` row.
  `pay_terms` lives on `contacts_cost` not `contacts`.
- Numbering: `invoice.type_id` assigned by a BEFORE INSERT trigger,
  resets per year.

## Services (`Services/`)
- 3-level hierarchy: Service Type → Category → Heading. `services` (main),
  `rate_billable` (rate card entries).

## Timesheet (`Timesheet/`)
- `time_cards` (50+ fields): `staff`, `date`, `total_hrs`, `type_of_time`,
  `submitted`, `approv` (N/Y/P/C). Pay period automation: Daily, Weekly,
  Bi-weekly, Monthly, Semi-monthly, Custom.

## Inventory (`Inventory/`)
- `inventory` (main), `inventory_change_log` (audit), `inventory_qty`
  (per-bin quantities), `inventory_attr` (per-bin attributes).
- **Quantity is stored in TWO tables and both must be written**:
  `inventory.quantity` (dashboard "Total Qty") and `inventory_qty.quantity`
  (per-warehouse views). Same dual-write pattern for bin assignment
  (`inventory.binid` vs `inventory_qty.binid`).

## Reports (`Reports/`)
- `Report.php` core class; `field_list.php` master registry (every report
  MUST be registered there). A report is enabled only when turned on in
  BOTH `reports_dashboard` AND `report_config`.
- Data-build gate: `isset($_POST['search_email_submit']) ||
  isset($_GET['post_encode'])` — NEVER `!empty($_POST)`.

## Security (`Security/`)
- `security_level_names`; `super` bypasses field permissions.
- **Tile access** across multiple roles is most-permissive; **field
  permissions** across multiple roles resolve least-restrictive via
  `array_intersect()`.
- `is_login.php` = session-level auth only; `checkAuthorised('tile_name')`
  = tile-level access. Both are needed; `is_login.php` alone is not
  tile-authorized.
- **`get_privileges()` default**: returns `'*'` (full/visible) when no
  privilege row exists — absence of a row means allowed, not denied.

## Calendar (`Calendar/`)
- `ticket_monthly_card.php` renders inside a loop — any new query MUST use
  batch prefetch or it causes N+1.

## Sales / Booking (`Sales/`, `Booking/`)
- `sales_lead_status` (CSV) does NOT include Won/Lost. `booking.salesid`
  links a booking to a sales lead; a resulting invoice references it via
  `invoice.bookingid`.

## FormBuilder (`FormBuilder/`)
- 40+ field types. SELECT = contact picker; SELECT_CUS = static dropdown.
  POST key: field `field_123` → `field_field_123`.

## Contacts (`Contacts/`)
- `contacts.tile_name`: 'contacts', 'vendors', or 'staff' (shared table).
  Encrypted name columns (`first_name`, `last_name`) cannot be
  searched/sorted in SQL — filtering happens in PHP after loading.
- New contacts created in a non-active `deleted` state until a detail is
  entered/activated.

## Email (`email.php`)
- `send_email()` is the core SwiftMailer send. Recipient suppression has
  three distinct concepts: Exclusion (per-send), Unsubscribe (permanent),
  Agreement (must have agreed).

## Cronjobs (`cronjobs/`)
- Bootstrap via relative path; set `$guest_access = true` before include.
  No `$_SESSION`/`$_GET`/`$_POST`; read config directly with `get_config()`.

## Global Search (`search.php`)
- Dual-mode: AJAX (10 results, one category) and non-AJAX advanced (500
  results, all categories with counts).

## Geo-Location Mobile App (`geo-location-app/`)
- Monolithic JSON REST API for the Flutter app (JWT auth). Depends on
  `php8_compatibility_fixes.php` being included by `shared_functions.php`.

## QB / Sage Export
- Invoice/PO/Contacts each expose `qb_export` (IIF) / CSV / Sage actions.
  `invoice.exported`: 0=needs export, 1=exported, 2=voided after export.

## Cross-Cutting Behaviors & Traps
- **`config_safe_str()` read/write symmetry** — reader must apply it too or
  the lookup silently misses.
- **`strpos()` on comma-separated config values false-positives** on
  overlapping substrings — use `FIND_IN_SET` or wrap both sides in commas.
- **Comma-wrapped config is never `empty()`** — test the raw `get_config()`
  value before wrapping.
- **Wrong config source returns empty silently** — `field_config` tables
  and `general_configuration` are different stores.
- **RDS `AUTO_INCREMENT` reads stale** — after `ALTER TABLE ...
  AUTO_INCREMENT = N` on RDS, run `ANALYZE TABLE tablename` to refresh
  metadata.
- **CLI vs web DB selection** — `db_connect.php` selects the DB differently
  under CLI; confirm the target customer DB before trusting CLI query
  results.

## MySQL Login Functions (ff_encrypt / ff_decrypt)
Some customer databases use MySQL stored functions `ff_encrypt()` /
`ff_decrypt()` for password comparison in the login query. If missing,
login silently fails with "invalid credentials" and no error.
