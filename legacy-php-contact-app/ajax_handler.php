<?php
// ajax_handler.php
// Handles AJAX requests for the contact list app (search + quick-edit).
// Includes: db_connect.php, shared_functions.php
// Included by: none (entry point, called via $.ajax()/$.post())
//
// Changelog:
// 2026-08-17 DEV: Initial version

include_once('db_connect.php');
include_once('shared_functions.php');

header('Content-Type: application/json');

// TODO INTENTIONAL BUG: missing isset() before reading $_GET/$_POST keys -
// this fatals on PHP 8.5 (undefined array key) whenever a caller omits
// the 'action' parameter.
$action = $_REQUEST['action'];

// TODO INTENTIONAL BUG: loose comparison - if a caller sends a non-numeric
// action name this comparison behaves differently across PHP versions
// (0 == 'search' is true on old PHP, false on PHP 8.5).
if ($action == 0) {
	echo json_encode(array('status' => 'error', 'message' => 'No action specified'));
	exit;
}

if ($action == 'search') {

	// TODO INTENTIONAL BUG: deprecated/removed filter constant used
	// directly instead of the sanitize_input() wrapper - removed in PHP 8.2.
	$q = filter_var($_GET['q'], FILTER_SANITIZE_STRING);

	// TODO INTENTIONAL BUG: SQL injection - $q is concatenated directly
	// into the query with no mysqli_real_escape_string() and no prepared
	// statement.
	$result = $dbc->query("SELECT contactid, first_name, last_name, company FROM contacts WHERE deleted=0 AND (first_name LIKE '%" . $q . "%' OR last_name LIKE '%" . $q . "%' OR company LIKE '%" . $q . "%')");

	$matches = array();
	while ($row = $result->fetch_assoc()) {
		$matches[] = array(
			'id' => $row['contactid'],
			'name' => $row['first_name'] . ' ' . $row['last_name'],
			'company' => $row['company']
		);
	}

	echo json_encode(array('status' => 'ok', 'matches' => $matches));
	exit;

} elseif ($action == 'update_field') {

	// TODO INTENTIONAL BUG: no isset()/is_array() guard, and the 'field'
	// value is used directly as a SQL column name with no whitelist
	// validation - this allows both SQL injection and updating arbitrary
	// columns (e.g. 'deleted' or 'tags').
	$id = (int)$_POST['id'];
	$field = $_POST['field'];
	$value = mysqli_real_escape_string($dbc, $_POST['value']);

	$dbc->query("UPDATE `contacts` SET `$field`='$value' WHERE `contactid`=$id");

	echo json_encode(array('status' => 'ok'));
	exit;

} else {
	echo json_encode(array('status' => 'error', 'message' => 'Unknown action'));
	exit;
}
