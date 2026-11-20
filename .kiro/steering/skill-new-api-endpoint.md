---
inclusion: auto
description: "Use when creating a new API endpoint, adding a Lambda function, or extending the REST API with a new route"
---

# Skill: Create New API Endpoint

## Workflow

When adding a new API endpoint to the portfolio risk dashboard (or any Serverless Framework project), follow these steps in order:

### Step 1: Create the Lambda Handler

Create a new file in `backend/src/routes/` or add to an existing one:

```javascript
// backend/src/routes/newResource.js
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, QueryCommand } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);
const TABLE_NAME = process.env.TABLE_NAME;

export const getResource = async (event) => {
  try {
    const { id } = event.pathParameters || {};
    if (!id) {
      return { statusCode: 400, body: JSON.stringify({ message: 'ID is required' }) };
    }

    const result = await docClient.send(new QueryCommand({
      TableName: TABLE_NAME,
      KeyConditionExpression: 'PK = :pk',
      ExpressionAttributeValues: { ':pk': `RESOURCE#${id}` },
    }));

    return { statusCode: 200, body: JSON.stringify(result.Items) };
  } catch (error) {
    console.error('Error:', error);
    return { statusCode: 500, body: JSON.stringify({ message: 'Internal server error' }) };
  }
};
```

### Step 2: Register in serverless.yml

Add the function definition under `functions:`:

```yaml
  newFunction:
    handler: src/routes/newResource.getResource
    timeout: 10
    events:
      - httpApi:
          path: /resources/{id}
          method: get
```

### Step 3: Add IAM Permissions (if needed)

If the function accesses new AWS services, add to `provider.iam.role.statements`.

### Step 4: Update Frontend API Client

Add the corresponding API call in `frontend/src/api/`:

```javascript
import { get } from 'aws-amplify/api';

export const fetchResource = async (id) => {
  const response = await get({ apiName: 'portfolioApi', path: `/resources/${id}` });
  return response.body.json();
};
```

### Step 5: Test

```bash
cd backend
npx serverless deploy --stage dev
curl https://API_ID.execute-api.eu-west-1.amazonaws.com/resources/123
```

## Checklist

- [ ] Handler uses named export matching serverless.yml function name
- [ ] Input validation with 400 response for bad requests
- [ ] Try/catch with 500 response (no internal details exposed)
- [ ] Timeout set appropriately (10s standard, 30s for Bedrock)
- [ ] IAM permissions scoped to minimum required actions
- [ ] CORS handled by provider-level `httpApi.cors: true`
