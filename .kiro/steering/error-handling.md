---
inclusion: auto
description: "Use when implementing error handling, adding try/catch blocks, handling API failures, or building resilient Lambda functions"
---

# Error Handling Standards

## Lambda API Responses

Always return structured error responses with appropriate HTTP status codes:

```javascript
// Success
return { statusCode: 200, body: JSON.stringify(data) };

// Client error (bad input)
return { statusCode: 400, body: JSON.stringify({ message: 'Missing required parameter: id' }) };

// Not found
return { statusCode: 404, body: JSON.stringify({ message: 'Client not found' }) };

// Server error (never expose internals)
return { statusCode: 500, body: JSON.stringify({ message: 'Internal server error' }) };
```

## Try/Catch Pattern

```javascript
export const handler = async (event) => {
  try {
    // Validate input
    const { id } = event.pathParameters || {};
    if (!id) {
      return { statusCode: 400, body: JSON.stringify({ message: 'Client ID is required' }) };
    }

    // Business logic
    const result = await fetchData(id);
    if (!result) {
      return { statusCode: 404, body: JSON.stringify({ message: `Client ${id} not found` }) };
    }

    return { statusCode: 200, body: JSON.stringify(result) };
  } catch (error) {
    console.error('Handler error:', { error: error.message, stack: error.stack });
    return { statusCode: 500, body: JSON.stringify({ message: 'Internal server error' }) };
  }
};
```

## Bedrock-Specific Errors

```javascript
try {
  const response = await bedrockClient.send(command);
  // parse response...
} catch (error) {
  if (error.name === 'ThrottlingException') {
    return { statusCode: 429, body: JSON.stringify({ message: 'AI service is busy. Please try again shortly.' }) };
  }
  if (error.name === 'ModelTimeoutException') {
    return { statusCode: 504, body: JSON.stringify({ message: 'AI request timed out. Please try again.' }) };
  }
  throw error; // Re-throw unexpected errors to outer catch
}
```

## Frontend Error Handling

- Show Cloudscape `Alert` with type "error" for API failures
- Provide a retry action where appropriate
- Never show raw error messages or stack traces to users
- Use `Flashbar` for transient errors that auto-dismiss

## Rules

- Log errors with `console.error` (CloudWatch captures these)
- Never expose stack traces, internal paths, or AWS resource names to clients
- Validate all input before processing (path params, query strings, body)
- Return user-friendly messages — not technical jargon
- For Bedrock: always handle throttling and timeout gracefully
