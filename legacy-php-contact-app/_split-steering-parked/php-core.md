---
inclusion: always
---

# PHP Compatibility — Critical Subset

Full detail lives in `php-compat.md` (loaded automatically when reviewing
PHP files, or on-demand). This file is the always-on quick reference every
agent needs regardless of domain.

## Dual Version Support
- **MANDATORY**: All code MUST work on BOTH PHP 5.6 AND PHP 8.5.
- **Null Coalescing (`??`)**: does NOT exist in PHP 5.6 — fatal parse error.
  Use `isset($var) ? $var : $default`.
- **Nullsafe Operator (`?->`)**: PHP 8.0+ only — do not use.
- **Deprecated/removed functions**: never use `each()`, `create_function()`,
  `FILTER_SANITIZE_STRING`, `mysql_*`, `ereg()`/`eregi()`/`split()`/`spliti()`,
  `get_magic_quotes_gpc()`, `$HTTP_RAW_POST_DATA`, curly-brace string access
  (`$str{0}`), unparenthesized nested ternaries.
- **Language when flagging**: only say "PHP 5.6" / "PHP 8.5" — never
  intermediate versions. Say "will not work on PHP X" or "fatal error on
  PHP X", not "notice"/"warning" (exception: an undefined variable/array
  index is described as an "error on PHP 8.5").

## Safe Wrapper Quick Reference
| Use This | Instead Of | Behavior on null/invalid |
|---|---|---|
| `safe_explode($delimiter, $string)` | `explode()` | Returns `array()` |
| `safe_implode($separator, $array)` | `implode()` | Returns `''` |
| `safe_count($var)` | `count()` | Returns `0` |
| `safe_array($var)` | Array cast | Returns `array()` |
| `safe_string($var)` | String cast | Returns `''` |
| `safe_in_array($needle, $haystack)` | `in_array()` | Returns `false` |
| `safe_array_filter($array)` | `array_filter()` | Returns `array()` |
| `sanitize_input($variable, $flag)` | `filter_var()` w/ deprecated flags | Handles null + deprecated flags |

Use a safe wrapper whenever the value comes from a DB query, `$_GET`,
`$_POST`, a function return, or any other nullable source. A hardcoded
literal, or a value already validated with `isset()`/type-checked
immediately before, may use the native function.

## Loose Comparison Trap
`0 == "foo"` is `false` on PHP 8.5 but was often `true`-ish behavior assumed
on older PHP. Prefer strict `===`/`!==` whenever one side could be an
integer `0` and the other a non-numeric string.
