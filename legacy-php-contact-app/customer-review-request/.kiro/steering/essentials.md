---
inclusion: always
---
# ExampleApp Essentials

**Version: 2026-08-19**
**Applies to: All Developers**

This is the only steering file loaded on every interaction. It holds the rules that apply regardless of what is being changed. Everything else is split by topic and loaded on demand.

---

## Steering Map — read the file that matches the work

| Working on | Read this file first |
|---|---|
| PHP logic, null safety, PHP 5.6/8.5 compatibility, SQL, schema, performance | `.kiro/steering/php-standards.md` |
| jQuery, AJAX calls, event binding, client-side widgets | `.kiro/steering/javascript-standards.md` |
| HTML structure, CSS/theme, layout, UI/UX, PDF output | `.kiro/steering/html-css-standards.md` |
| Authorization, permissions, input validation, SQL injection, uploads, sessions | `.kiro/steering/security-standards.md` |
| Code review, QA, branches and commits, ticket notes, local dev environment | `.kiro/steering/qa-process.md` |
| Bootstrap, config system, tile/AJAX architecture, shared helper functions | `.kiro/steering/architecture-patterns.md` |
| A specific tile's internals (Ticket, Invoice, PO, Inventory, Reports, …) | `.kiro/steering/module-knowledge.md` |

Read the matching file(s) **before** writing or reviewing code in that domain — do not work from memory of these standards. A single `.php` file normally mixes PHP, SQL, JavaScript, HTML and CSS, so load every file that matches the change, not just one. When the task names a tile (Ticket, Invoice, Purchase Order, Inventory, Reports, …), also read that tile's section in `module-knowledge.md`.

---

## Non-Negotiables (every change, every file)

- Code MUST work on BOTH PHP 5.6 AND PHP 8.5. `??`, `?->`, strict type declarations, the spread operator in declarations and `::class` on objects each fatal on one of the two versions — never use them
- Never trust `$_POST` / `$_GET` / `$_REQUEST` / `$_FILES`: `isset()` before access, sanitize per type, escape or use a prepared statement before SQL
- Never pass a possibly-null value into a native string/array function — use the `safe_*` wrappers (`safe_explode`, `safe_count`, `safe_in_array`, `safe_implode`, `safe_string`, `safe_array_filter`)
- Rows are never removed with `DELETE FROM` — soft delete via the `deleted` column
- Database schema changes go through `db_structure/` then `php db_update.php` — never run ALTER/CREATE directly
- New functionality is controlled by a configuration option that defaults to OFF; new restricted functionality gets a NEW security privilege, never a reused one
- Match existing patterns: no frameworks, no Composer packages, no new build tools
- `php -l` must pass on every modified file before committing
- These standards apply to NEW code. Minor changes to existing lines do not require rewriting the surrounding code to comply

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

---

## Error Handling

- Never show raw PHP errors/warnings to end users
- Functions return predictable types on failure (empty array, false, null)
- External connections wrapped in try/catch — never let an external service failure crash the page
- Always return valid JSON from AJAX endpoints with a success/error indicator

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
