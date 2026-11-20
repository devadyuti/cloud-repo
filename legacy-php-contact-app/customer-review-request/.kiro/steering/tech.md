---
inclusion: always
---

# Technology Stack

## Languages & Platform

- **PHP** — primary server-side language. Code MUST work on BOTH PHP 5.6 AND PHP 8.5 (see `essentials.md` and `php-standards.md`).
- **JavaScript** — jQuery, jQuery UI, Select2, DataTables, Chart.js.
- **SQL** — MySQL 8.0 via the MySQLi extension.
- **HTML5 / CSS3** — Bootstrap 3.x framework.

## Database

- MySQL 8.0, InnoDB, utf8mb4.
- Global `$dbc` connection variable.
- Multiple databases: DATABASE_NAME, DATABASE_NAME2, DATABASE_COPY2.
- Local naming: `local_{customer}`; remote: `{customer}_live_db`.
- Soft deletes via `deleted` field.
- Schema changes go through `db_structure/` (db_tables.php, db_fields.php, db_indexes.php) then `php db_update.php` — NEVER run ALTER/CREATE directly.

## Key Libraries

- **TCPDF / FPDF / FPDI** — PDF generation.
- **PHPExcel** — Excel import/export.
- **TinyMCE** — rich text editing.
- **SwiftMailer 5.x** — email.
- **Mobile_Detect**, **OAuth PHP**, **MRBS**, **EasyPost**, **Twilio**.

## Infrastructure

- Apache 2.4+ (or Nginx + PHP-FPM).
- AWS: EC2, RDS (MySQL), S3, CloudWatch, ELB, Auto Scaling.
- AWS CLI profiles: `prod` (prod EC2/Apache/PHP logs), `dev` (production RDS/MySQL logs), `demo`, `product`.

## Bootstrap & Patterns

- `include.php` is the master bootstrap — always included first.
- Helper functions: `get_config()`, `get_contact()`, `get_field_value()`.
- Custom database-backed sessions; close early with `session_write_close()`.
- Prepared statements or proper escaping for all user input.
- Performance tracking via `$_SERVER['page_load_info']`; query/error logging in debug mode.

## Local Testing

- Bypass login: set `DEFINE('DEBUG', 1);` in `/var/www/html/db_details/localhost.inc`, then set back to `0` immediately after.
- Restart PHP-FPM after editing PHP files when debugging live (OPcache).
