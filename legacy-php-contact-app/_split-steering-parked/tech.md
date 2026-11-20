---
inclusion: always
---

# Tech Stack (Version Lock)

- **Language**: PHP — MUST run on both PHP 5.6 AND PHP 8.5. This is the
  single most important constraint on any code review or code change here.
- **Database**: MySQL via `mysqli` (OO style preferred: `$dbc->query()`,
  `$dbc->real_escape_string()`). No ORM, no query builder.
- **Frontend JS**: jQuery only. No ES6, no build step, no bundler.
- **No framework**: no Composer autoloading, no MVC, no modern JS bundler.
  Entry points are standalone `.php` files. Do not introduce new paradigms.
- **Server**: Apache + PHP-FPM.
- **Line endings**: CRLF throughout (do not auto-convert).

Do not suggest or introduce: Composer packages, a PHP framework (Laravel,
Symfony, Slim), a JS framework/bundler, TypeScript, or ORMs. Matching the
existing procedural, mixed PHP/HTML/CSS/JS style is correct for this
codebase, not a smell to "fix."
