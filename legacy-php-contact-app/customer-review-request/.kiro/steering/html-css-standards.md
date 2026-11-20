---
inclusion: manual
---
# HTML, CSS and UI/UX Standards

Load when the work involves markup, styling, layout, responsive/accordion views, slider and card UI, or PDF output. Colour and size rules exist so customer themes can override them — treat them as functional, not cosmetic.

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

## Scrolling Rules

- Pages should not scroll — only the content area scrolls
- Never have overlapping/nested scrollbars (vertical within vertical, or horizontal within horizontal)
- If an exception is needed, confirm with the project lead

---

## PDF

- TCPDF is used to generate PDF files
- Supported CSS is limited — inline styles are acceptable here (and only here)
- For PDFs that embed/import existing PDF pages, the MYPDF class extends `\setasign\Fpdi\Tcpdf\Fpdi` (see `Estimate/estimate_pdf_output.php`)

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
