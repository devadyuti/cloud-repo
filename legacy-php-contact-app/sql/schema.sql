-- schema.sql
-- ExampleApp Contact List (sample legacy PHP app)
-- Database structure for the mock contact list app used to validate the
-- Kiro QA review agents. Mirrors the table shape from the project spec.
--
-- Changelog:
-- 2026-08-17 DEV: Initial version

CREATE TABLE IF NOT EXISTS `contacts` (
	`contactid` INT AUTO_INCREMENT PRIMARY KEY,
	`first_name` VARCHAR(100),
	`last_name` VARCHAR(100),
	`email` VARCHAR(255),
	`phone` VARCHAR(50),
	`company` VARCHAR(200),
	`tags` VARCHAR(255),
	`created_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`deleted` INT(1) DEFAULT 0
);

-- Sample rows for local testing
INSERT INTO `contacts` (`first_name`, `last_name`, `email`, `phone`, `company`, `tags`, `deleted`) VALUES
('Jane', 'Doe', 'jane.doe@example.com', '555-0100', 'Acme Corp', 'lead,vip', 0),
('John', 'Smith', 'john.smith@example.com', '555-0101', 'Globex Inc', 'customer', 0),
('Priya', 'Nair', 'priya.nair@example.com', '555-0102', 'Initech', NULL, 0);
