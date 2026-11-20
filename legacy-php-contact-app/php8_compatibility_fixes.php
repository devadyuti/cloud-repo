<?php
// php8_compatibility_fixes.php
// Polyfills and constant fallbacks that let the codebase run on both
// PHP 5.6 and PHP 8.5. Included by: shared_functions.php
// Includes: none
//
// Changelog:
// 2026-08-17 DEV: Initial version

// FILTER_SANITIZE_STRING / FILTER_SANITIZE_STRIPPED were removed in PHP 8.2.
// Polyfilled here so legacy call sites do not fatal, but new code should use
// FILTER_SANITIZE_FULL_SPECIAL_CHARS via sanitize_input() instead.
if (!defined('FILTER_SANITIZE_STRING')) {
	define('FILTER_SANITIZE_STRING', 513);
}
if (!defined('FILTER_SANITIZE_STRIPPED')) {
	define('FILTER_SANITIZE_STRIPPED', 513);
}

// str_contains()/str_starts_with()/str_ends_with() do not exist on PHP 5.6.
if (!function_exists('str_contains')) {
	function str_contains($haystack, $needle) {
		if ($needle === '') {
			return true;
		}
		return strpos($haystack, $needle) !== false;
	}
}

if (!function_exists('str_starts_with')) {
	function str_starts_with($haystack, $needle) {
		return substr($haystack, 0, strlen($needle)) === $needle;
	}
}

if (!function_exists('str_ends_with')) {
	function str_ends_with($haystack, $needle) {
		if ($needle === '') {
			return true;
		}
		return substr($haystack, -strlen($needle)) === $needle;
	}
}
