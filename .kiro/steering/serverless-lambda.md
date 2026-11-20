---
inclusion: fileMatch
fileMatchPattern: "**/backend/**,**/serverless.yml,**/routes/**,**/services/**"
---

# Serverless & Lambda Guidelines

## Lambda Handler Pattern

```javascript
// src/routes/resource.js
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

export const handlerName = async (event) => {
  try {
    const { id } = event.pathParameters || {};

    // Business logic here

    return {
      statusCode: 200,
      body: JSON.stringify(data),
    };
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Internal server error' }),
    };
  }
};
```

## Serverless Framework 4 Conventions

- **One function per endpoint** — never bundle multiple routes into one Lambda
- **httpApi** (HTTP API v2) — not restApi (REST API v1)
- **CORS:** Enabled at the provider level (`httpApi.cors: true`)
- **Timeouts:** 10s default, 30s for Bedrock calls
- **Stage:** Parameterised via `${opt:stage, 'dev'}`

## DynamoDB Single-Table Design

- **PK:** Entity identifier (e.g., `CLIENT#CLT001`)
- **SK:** Sort key for relationships (e.g., `PROFILE`, `PORTFOLIO`, `HOLDING#001`)
- **BillingMode:** PAY_PER_REQUEST (on-demand)
- **No GSIs** unless explicitly needed

## Amazon Bedrock Integration

```javascript
import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';

const bedrockClient = new BedrockRuntimeClient({ region: 'eu-west-1' });

const invokeModel = async (prompt) => {
  const command = new InvokeModelCommand({
    modelId: 'eu.anthropic.claude-sonnet-4-6',
    contentType: 'application/json',
    body: JSON.stringify({
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    }),
  });
  const response = await bedrockClient.send(command);
  return JSON.parse(new TextDecoder().decode(response.body));
};
```

## IAM Permissions

- Use least-privilege — only the DynamoDB actions and Bedrock actions needed
- Wildcard region for Bedrock inference profiles: `arn:aws:bedrock:*:ACCOUNT:inference-profile/*`
- Scope DynamoDB permissions to the specific table ARN

## Error Handling

- Always return proper HTTP status codes (200, 400, 404, 500)
- Log errors with `console.error` (CloudWatch picks these up)
- Never expose internal error details to the client
- Validate path parameters and request body before processing
