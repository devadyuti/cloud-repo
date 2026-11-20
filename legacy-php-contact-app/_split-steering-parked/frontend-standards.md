---
inclusion: auto
name: frontend-standards
description: JavaScript, CSS, and HTML standards for legacy PHP pages — jQuery/ES5 compatibility, AJAX error handling, no !important, no px units, HTML validity. Use when reviewing or writing JS, CSS, or HTML in this codebase.
---

# JavaScript Standards

## Compatibility
- Use `var` over `let`/`const` unless browser support is confirmed.
- Flag a `const` that is later reassigned (fails silently / errors
  depending on engine) — prefer `var`.
- Avoid arrow functions (`=>`) if legacy browser support needed.
- No ES6 default parameters (`function fn(x, y = true) {}`) — write the
  default explicitly:
  `function fn(x, y) { if (y === undefined) { y = true; } }`.
- Use `$.ajax()` — avoid `fetch()` without polyfill confirmation.
- Always use `encodeURIComponent()` when building URLs with dynamic values:
  ```javascript
  url: 'page.php?tile_name=' + encodeURIComponent(tile_name) + '&category=' + encodeURIComponent(category)
  ```

## Event Binding
- Delegated events for dynamically loaded content:
  `$(document).on('click', '.selector', fn)`.
- Avoid inline `onclick` attributes — use unobtrusive JavaScript.
- Use namespaced events with `.off()` before `.on()` to prevent handler
  stacking.

## AJAX Error Handling
An error callback on `$.ajax()` / `$.post()` write calls is recommended
(flag as **Minor** when missing, never a blocker):
```javascript
$.post('endpoint.php', data).fail(function() {
    alert('An error occurred. Please try again.');
});
```

## DOM Safety
- Check element existence: `if ($('#el').length)`.
- Escape user-generated content before DOM insertion.
- `.every()` on empty arrays returns `true` — guard with `arr.length > 0 &&`
  first.

---

# CSS Standards

- No inline styles on screen (exceptions: `display:none` for JS toggling,
  PDF output, progress bar width/color).
- Colors defined ONLY in theme stylesheets — never inline.
- **Never use `!important`.**
- All size units in vh/vw or em — never px.
- JS functional selectors (underscore-separated) and CSS styling selectors
  (dash-separated) are intentionally distinct.
- **Selector compatibility:** `:not(td)` is valid CSS; `:not('td')` (quoted)
  is invalid and silently fails — never quote the argument to `:not()`.

---

# HTML Standards

- Meet W3C standards (testable at validator.w3.org).
- No whitespace before the first `<?php` or `<html>` tag.
- Double quotes for all HTML tag attributes (`name="example"`).
- Do not use HTML `id` attributes — select by class, type, and relative
  position.
- Never use short open tags (`<?`) for output — use `<?=`. `<?` depends on
  the `short_open_tag` ini setting and silently outputs nothing when
  disabled.
- Table column count: when a `<th>` is conditionally rendered, the
  corresponding `<td>` must use the exact same condition.

---

# Scrolling Rules

- Pages should not scroll — only the content area scrolls.
- Never have overlapping/nested scrollbars.

---

# UI / UX Style Guide (New Code Only)

Violations are Minor unless they break theme compatibility.

- No black box around content; no gray background for content.
- No blue background for accordion content (should be white).
- No inline styles (except `display:none` and PDF output).
- No links in headers — icons only.
- When adding a background color, always add a text color for readability.
- Use CSS classes, never hardcoded styles (so themes can override).
- Search begins only on Search button click.
- Required-field asterisk appears after the label colon with a leading
  space (e.g. `List Name: *`).

## Tables
- Header in theme color, left-aligned; numeric data right-aligned; sticky
  header on scroll.
- Display headers even when the table is empty.
- Alternating rows via `.table-striped` or `.row-even-bg`/`.row-odd-bg`.
