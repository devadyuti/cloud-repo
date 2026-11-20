---
inclusion: manual
---
# JavaScript Standards — jQuery, AJAX, Client-Side Behaviour

Load when the work involves JavaScript, jQuery, AJAX calls, event binding or client-side widgets. Server-side AJAX endpoint rules (`ob_clean()` handling, response shape, sanitization) are in `php-standards.md` and `security-standards.md`.

---

## Client-Side Standards

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

## AJAX Patterns
- Avoid reloading the entire page — use AJAX to reload only the section that needs updating
- When adding a new entry, nothing should be added to the database until a detail is entered (e.g., a name or business)
- AJAX responses: HTML for page insertion, JSON with a `status` attribute, or empty/no response are all acceptable existing patterns. New endpoints should prefer JSON with a status indicator (guideline for new code, not a blocker)
- AJAX should use the full URL path for referenced files
- An error callback on `$.ajax()` / `$.post()` write calls is recommended — flag as Minor when missing, never Major or Critical
