---
inclusion: always
---

# Product Overview

ExampleApp is a legacy PHP business-management platform (tickets, purchase
orders, invoicing, inventory, CRM). It runs on Apache + MySQL with no
framework — standalone `.php` files bootstrapped by `include.php`, tile-based
feature areas, AJAX routed through centralized handlers.

This repository contains a **sample contact list app** — a small, self
contained slice of ExampleApp (index/contacts/AJAX handler/DB connect/shared
functions) used to validate that the Kiro QA review agents in `.kiro/agents/`
correctly catch real ExampleApp coding-standard violations. The sample app
is not the deliverable; the review agents and steering are.

Multi-tenant in the real product: each customer has its own database with its
own configuration, contacts, and data — the same tile can behave differently
per customer because labels, statuses and enabled features are config-driven.

## Scope note for QA reviews
This sample app intentionally has NO `include.php` bootstrap, NO login
system, and NO `checkAuthorised()` calls — those belong to the full
ExampleApp platform and are out of scope for this trimmed-down demo. Do
NOT flag a missing `checkAuthorised()`, missing session/auth check, or
missing tile-permission check as an issue here; it is expected. Security
review should focus on what IS present: SQL injection, input validation,
hardcoded secrets, and output/escaping — not the absence of the full
platform's auth layer.
