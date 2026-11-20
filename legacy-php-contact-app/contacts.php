<?php
// contacts.php
// Full contact CRUD (add / edit / delete), inline form.
// Includes: db_connect.php, shared_functions.php
// Included by: none (entry point)
//
// Changelog:
// 2026-08-17 DEV: Initial version

include_once('db_connect.php');
include_once('shared_functions.php');

// Handle new contact submission.
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) && $_POST['action'] == 'add') {

	$first_name = mysqli_real_escape_string($dbc, sanitize_input($_POST['first_name'], FILTER_SANITIZE_FULL_SPECIAL_CHARS));
	$last_name = mysqli_real_escape_string($dbc, sanitize_input($_POST['last_name'], FILTER_SANITIZE_FULL_SPECIAL_CHARS));
	$email = mysqli_real_escape_string($dbc, sanitize_input($_POST['email'], FILTER_SANITIZE_FULL_SPECIAL_CHARS));
	$phone = mysqli_real_escape_string($dbc, sanitize_input($_POST['phone'], FILTER_SANITIZE_FULL_SPECIAL_CHARS));

	// TODO INTENTIONAL BUG: '' == 0 is true on PHP 5.6/older but false on
	// PHP 8.5, so this "was company left blank" check silently stops
	// working once the app moves to 8.5.
	if ($_POST['company'] == 0) {
		$company = '';
	} else {
		$company = mysqli_real_escape_string($dbc, sanitize_input($_POST['company'], FILTER_SANITIZE_FULL_SPECIAL_CHARS));
	}

	// TODO INTENTIONAL BUG: explode() directly on $_POST['tags'] with no
	// isset()/safe_explode() guard - fatals on PHP 8.5 when the tags field
	// is omitted from the request (explode(string, null) is a TypeError).
	$tag_parts = explode(',', $_POST['tags']);
	$tags = mysqli_real_escape_string($dbc, implode(',', array_map('trim', $tag_parts)));

	$dbc->query("INSERT INTO `contacts` (`first_name`,`last_name`,`email`,`phone`,`company`,`tags`,`deleted`) VALUES ('$first_name','$last_name','$email','$phone','$company','$tags',0)");

	header('Location: contacts.php');
	exit;
}

// Handle delete.
// TODO INTENTIONAL BUG: SQL injection - $_GET['id'] is concatenated
// straight into the query with no sanitization, no (int) cast, and no
// real_escape_string().
if (isset($_GET['action']) && $_GET['action'] == 'delete') {
	$dbc->query("DELETE FROM contacts WHERE contactid = " . $_GET['id']);
	header('Location: contacts.php');
	exit;
}

$list_result = $dbc->query("SELECT `contactid`, `first_name`, `last_name`, `email`, `phone`, `company`, `tags` FROM `contacts` WHERE `deleted`=0 ORDER BY `last_name`");
?>
<!DOCTYPE html>
<html>
<head>
	<title>ExampleApp Contact List - Contacts</title>
	<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
	<style>
		/* TODO INTENTIONAL BUG: !important overuse - never use !important
		   per CSS standards, it breaks theme overrides. */
		.contact-row {
			color: #333 !important;
			background-color: #fff !important;
		}
		.contact-table th {
			background-color: #ececec !important;
		}
	</style>
</head>
<body>
	<h1>Contacts</h1>

	<h2>Add Contact</h2>
	<form method="post" action="contacts.php">
		<input type="hidden" name="action" value="add">
		<input type="text" name="first_name" placeholder="First Name" required>
		<input type="text" name="last_name" placeholder="Last Name" required>
		<input type="text" name="email" placeholder="Email">
		<input type="text" name="phone" placeholder="Phone">
		<input type="text" name="company" placeholder="Company">
		<input type="text" name="tags" placeholder="Tags (comma separated)">
		<button type="submit">Add Contact</button>
	</form>

	<h2>All Contacts</h2>
	<table class="contact-table" border="1">
		<tr>
			<th>Name</th>
			<th>Email</th>
			<th>Phone</th>
			<th>Company</th>
			<th>Tags</th>
			<th>Actions</th>
		</tr>
		<?php while ($contact = $list_result->fetch_assoc()) { ?>
		<tr class="contact-row" data-id="<?= (int)$contact['contactid'] ?>">
			<td class="editable-name"><?= htmlspecialchars($contact['first_name'].' '.$contact['last_name']) ?></td>
			<td><?= htmlspecialchars(safe_string($contact['email'])) ?></td>
			<td><?= htmlspecialchars(safe_string($contact['phone'])) ?></td>
			<td><?= htmlspecialchars(safe_string($contact['company'])) ?></td>
			<td><?= htmlspecialchars(safe_string($contact['tags'])) ?></td>
			<td>
				<a href="#" class="quick-edit" data-id="<?= (int)$contact['contactid'] ?>">Edit</a>
				&nbsp;|&nbsp;
				<a href="contacts.php?action=delete&id=<?= (int)$contact['contactid'] ?>" onclick="return confirm('Delete this contact?');">Delete</a>
			</td>
		</tr>
		<?php } ?>
	</table>

	<script>
		// Quick inline-edit: prompt for a new company name and save via AJAX.
		$(document).on('click', '.quick-edit', function(e) {
			e.preventDefault();
			var contactid = $(this).data('id');
			var new_company = prompt('New company name:');
			if (new_company === null) {
				return;
			}

			// TODO INTENTIONAL BUG: debug code left in.
			console.log('Saving company for contact', contactid, new_company);

			// TODO INTENTIONAL BUG: no .fail() error handler on this write
			// call - a failed save gives the user no feedback at all.
			$.post('ajax_handler.php', {
				action: 'update_field',
				id: contactid,
				field: 'company',
				value: new_company
			}, function(response) {
				location.reload();
			});
		});
	</script>
</body>
</html>
