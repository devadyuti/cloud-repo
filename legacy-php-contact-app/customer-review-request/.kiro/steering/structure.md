---
inclusion: always
---

# Project Structure

## Core System Files (root)

- `include.php` — master bootstrap (system initialization).
- `global.php` — security, constants, access control.
- `function.php` — core business logic (~1.5MB). Never read whole; navigate by symbol/grep.
- `db_connect.php` — database connections.
- `session_set.php` / `sessions.php` — session constants and DB-backed session handler.
- `header.php` / `footer.php` / `tiles.php` / `navigation.php` — UI framework.
- `ajax_all.php` — global AJAX handler (~231KB).

## Module Layout

Each business module is its own top-level directory (Contacts/, Ticket/, Timesheet/, Invoice/, Estimate/, Inventory/, Equipment/, Project/, FormBuilder/, Reports/, Dispatch/, HR/, Safety/, etc.).

## File Naming Conventions

- `index.php` / `main.php` — module entry point.
- `config.php` — module configuration and field definitions.
- `*_ajax.php` — AJAX request handlers (action-parameter routing).
- `field_config*.php` — field configuration interfaces.
- `add_*.php` — add/edit forms and accordion sections.
- `*_content.php` — display/content logic.
- `*_functions.php` — module-specific functions.

## Key Database Tables

- `contacts` — all contact/customer data.
- `tickets`, `ticket_attached`, `ticket_schedule`, `ticket_comment`, `ticket_checklist` — work ticket system.
- `time_cards`, `pay_period`, `holidays` — timesheet system.
- `inventory`, `projects`, `invoice`, `estimates` — core business data.
- `config` / `general_configuration` — system configuration (name/value; read via `get_config()`).
- `field_config_*` — per-module field configuration.
- Custom fields: `*_custom_fields` (definitions) + `*_custom_field_values` (data).

## Architectural Patterns

- Modular MVC-like structure with centralized bootstrap.
- Tile system for menu/module visibility and per-user ordering.
- Role-based access: `checkAuthorised()`, `tile_visible()`, `check_subtab_persmission()`.
- Field-level encryption via `encryptIt()` / `decryptIt()` for sensitive data.

## Knowledge & Rules

- `.kiro/steering/essentials.md` — the only always-loaded steering file (universal rules + steering map).
- `.kiro/steering/php-standards.md`, `javascript-standards.md`, `html-css-standards.md`,
  `security-standards.md`, `qa-process.md` — domain standards, read on demand for the work at hand.
- `.kiro/steering/architecture-patterns.md` — platform wiring, config system, shared helpers.
- `.kiro/steering/module-knowledge.md` — per-tile internals; read the section for the tile being changed.
