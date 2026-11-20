---
name: "amazon-internal"
displayName: "Amazon Internal Tools"
description: "Access Amazon internal systems - code search, wikis, ticketing, CRM (Sentral), email (Outlook), and Slack"
keywords: ["amazon", "internal", "wiki", "code", "search", "tickets", "sim", "sentral", "outlook", "email", "slack", "phonetool", "quip", "broadcast", "calendar"]
author: "demo-author"
---

# Overview

Bundle of Amazon internal MCP servers for productivity across code search, documentation, ticketing, CRM, email, and messaging.

## Available MCP Servers

### builder-mcp
Amazon's internal builder tools — code search, wiki, ticketing, internal search, and website reading.

**Tools:**
- `ReadInternalWebsites` - Read content from internal Amazon websites (code.amazon.com, w.amazon.com, phonetool, quip, etc.)
- `InternalCodeSearch` - Search source code across Amazon repositories
- `TicketingReadActions` - Search and read SIM-T tickets, resolver groups
- `InternalSearch` - Search across internal resources (wiki, BuilderHub, Sage, Broadcast, etc.)

### aws-sentral-mcp
Amazon CRM (Sentral) — opportunity management, account details, contacts, and spend data.

**Tools:**
- `get_opportunity_details` - Get opportunity details
- `search_opportunities` - Search opportunities
- `get_my_personal_details` - Get your personal details
- `search_accounts` - Search customer accounts
- `create_task` - Create tasks
- `list_account_tasks` - List account tasks
- `search_contacts` - Search contacts
- `fetch_contact_details` - Fetch contact details
- `get_account_spend_by_service` - Get account spend by service
- `fetch_account_details` - Fetch account details
- `search_products` - Search products
- `get_account_spend_summary` - Get account spend summary
- `search_users` - Search users

### aws-outlook-mcp
Outlook email and calendar access.

**Tools:**
- `email_search` - Search emails
- `email_contacts` - List contacts
- `calendar_availability` - Check availability
- `calendar_meeting` - Create/manage meetings
- `email_read` - Read email content
- `email_draft` - Draft emails
- `email_inbox` - View inbox
- `calendar_search` - Search calendar
- `calendar_view` - View calendar
- `email_attachments` - Access attachments

### slack-mcp
Slack messaging integration.

## Best Practices

- Use `InternalSearch` for broad queries, `InternalCodeSearch` for code-specific searches
- Use `ReadInternalWebsites` when you have a specific URL to read
- Sentral tools require appropriate permissions — use read-only operations when possible
- Email send/forward operations should be confirmed before execution
