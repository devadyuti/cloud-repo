<?php
// index.php
// Dashboard - contact count and recent activity.
// Includes: db_connect.php, shared_functions.php
// Included by: none (entry point)
//
// Changelog:
// 2026-08-17 DEV: Initial version

include_once('db_connect.php');
include_once('shared_functions.php');

// TODO INTENTIONAL BUG: no isset() guard on $_GET['search'] before use.
$search = $_GET['search'];

$where = '';
if ($search != '') {
	$safe_search = mysqli_real_escape_string($dbc, $search);
	$where = "AND (first_name LIKE '%$safe_search%' OR last_name LIKE '%$safe_search%')";
}

$result = $dbc->query("SELECT COUNT(*) AS total FROM `contacts` WHERE `deleted`=0 $where");
$row = $result->fetch_assoc();
$total_contacts = $row['total'];

// TODO INTENTIONAL BUG: debug code left in - dumps the count on every load.
var_dump($total_contacts);

$recent_result = $dbc->query("SELECT `contactid`, `first_name`, `last_name`, `company`, `created_date` FROM `contacts` WHERE `deleted`=0 ORDER BY `created_date` DESC LIMIT 5");
?>
<!DOCTYPE html>
<html>
<head>
	<title>ExampleApp Contact List - Dashboard</title>
	<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body>
	<h1>Dashboard</h1>

	<form method="get" action="index.php">
		<input type="text" name="search" value="<?= htmlspecialchars(safe_string($search)) ?>" placeholder="Search contacts...">
		<button type="submit">Search</button>
	</form>

	<p>Total Active Contacts: <?= (int)$total_contacts ?></p>

	<h2>Recent Activity</h2>
	<table border="1">
		<tr>
			<th>Name</th>
			<th>Company</th>
			<th>Created</th>
		</tr>
		<?php while ($recent_row = $recent_result->fetch_assoc()) { ?>
		<tr>
			<td><?= htmlspecialchars($recent_row['first_name'].' '.$recent_row['last_name']) ?></td>
			<td><?= htmlspecialchars($recent_row['company']) ?></td>
			<td><?= htmlspecialchars($recent_row['created_date']) ?></td>
		</tr>
		<?php } ?>
	</table>

	<p><a href="contacts.php">Manage Contacts</a></p>
</body>
</html>
