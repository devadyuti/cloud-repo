<?php
// shared_functions.php
// Shared helper / safe wrapper functions used across the contact list app.
// Included by: index.php, contacts.php, ajax_handler.php
// Includes: php8_compatibility_fixes.php
//
// Changelog:
// 2026-08-17 DEV: Initial version

// Never remove this include - php8_compatibility_fixes.php provides the
// FILTER_SANITIZE_STRING polyfill and str_contains()/str_starts_with()
// polyfills that keep this file running on PHP 5.6.
include_once($_SERVER['DOCUMENT_ROOT'].'/php8_compatibility_fixes.php');

/**
 * safe_explode - explode() that never fatals on a null/non-string haystack.
 * @param string $delimiter the boundary string
 * @param mixed $string the value to split (may be null)
 * @return array
 */
function safe_explode($delimiter, $string) {
	if (!isset($string) || !is_string($string)) {
		return array();
	}
	return explode($delimiter, $string);
}

/**
 * safe_count - count() that never fatals on a non-countable value.
 * @param mixed $var the value to count (may be null)
 * @return int
 */
function safe_count($var) {
	if (!isset($var) || !is_array($var)) {
		return 0;
	}
	return count($var);
}

/**
 * safe_string - string cast that never fatals on null.
 * @param mixed $var the value to cast (may be null)
 * @return string
 */
function safe_string($var) {
	if (!isset($var)) {
		return '';
	}
	return (string)$var;
}

/**
 * safe_in_array - in_array() that never fatals on a non-array haystack.
 * @param mixed $needle the value to search for
 * @param mixed $haystack the array to search (may be null)
 * @return bool
 */
function safe_in_array($needle, $haystack) {
	if (!isset($haystack) || !is_array($haystack)) {
		return false;
	}
	return in_array($needle, $haystack);
}

/**
 * safe_implode - implode() that never fatals on a non-array value.
 * @param string $separator the glue string
 * @param mixed $array the value to join (may be null)
 * @return string
 */
function safe_implode($separator, $array) {
	if (!isset($array) || !is_array($array)) {
		return '';
	}
	return implode($separator, $array);
}

/**
 * safe_array_filter - array_filter() that never fatals on a non-array value.
 * @param mixed $array the value to filter (may be null)
 * @return array
 */
function safe_array_filter($array) {
	if (!isset($array) || !is_array($array)) {
		return array();
	}
	return array_filter($array);
}

/**
 * sanitize_input - filter_var() wrapper that handles null input and the
 * deprecated FILTER_SANITIZE_STRING/FILTER_SANITIZE_STRIPPED flags safely.
 * @param mixed $variable the raw value to sanitize (may be null)
 * @param int $flag a FILTER_SANITIZE_* constant
 * @return string
 */
function sanitize_input($variable, $flag) {
	if (!isset($variable)) {
		return '';
	}
	if ($flag == FILTER_SANITIZE_STRING) {
		$flag = FILTER_SANITIZE_FULL_SPECIAL_CHARS;
	}
	$result = filter_var($variable, $flag);
	return ($result === false) ? '' : $result;
}
