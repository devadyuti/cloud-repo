---
name: "aws-docs"
displayName: "AWS Documentation & Diagrams"
description: "Search and read AWS documentation, get recommendations, and generate architecture diagrams"
keywords: ["aws", "documentation", "docs", "diagram", "architecture", "cloud", "service", "reference", "guide"]
author: "demo-author"
---

# Overview

AWS documentation search and architecture diagram generation. Use this power when working with AWS services, looking up API references, or creating architecture diagrams.

## Available MCP Servers

### aws-docs
Official AWS Documentation MCP server — search, read, and get recommendations from docs.aws.amazon.com.

**Tools:**
- `search_documentation` - Search AWS documentation using the official search API
- `read_documentation` - Fetch and convert an AWS documentation page to markdown
- `read_sections` - Extract specific sections from AWS documentation pages by title
- `recommend` - Get content recommendations for an AWS documentation page

### aws-diagram
AWS Architecture Diagram generator — create visual diagrams using the Python diagrams package.

**Tools:**
- `generate_diagram` - Generate a PNG diagram from Python code using the diagrams DSL
- `get_diagram_examples` - Get example code for different diagram types (aws, sequence, flow, k8s, etc.)
- `list_icons` - List available icons from the diagrams package with optional filtering

## Usage Examples

```javascript
// Search for documentation
search_documentation({ search_phrase: "Lambda function URLs", limit: 5 })

// Read a specific page
read_documentation({ url: "https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html" })

// Read specific sections
read_sections({
  url: "https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html",
  section_titles: ["Creating a function URL", "Security and auth model"]
})

// Get related pages
recommend({ url: "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html" })
```

## Best Practices

- Use `search_documentation` first to find relevant pages
- Use `read_sections` for targeted extraction rather than reading entire pages
- Use `recommend` to discover related content and newly released features
- For diagrams, call `list_icons` first to discover available icons, then `get_diagram_examples` for syntax
