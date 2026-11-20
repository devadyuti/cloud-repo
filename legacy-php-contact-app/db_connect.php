<?php
// db_connect.php
// Database connection for the ExampleApp Contact List sample app.
// Included by: index.php, contacts.php, ajax_handler.php
// Includes: none
//
// Changelog:
// 2026-08-17 DEV: Initial version

// TODO INTENTIONAL BUG: credentials are hardcoded here instead of being
// read from an environment variable or a config file outside the repo.
$db_host = 'localhost';
$db_user = 'root';
$db_pass = 'password123';
$db_name = 'contact_list';

$dbc = new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($dbc->connect_error) {
	die('Database connection failed: ' . $dbc->connect_error);
}
