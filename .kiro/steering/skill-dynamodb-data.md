---
inclusion: auto
description: "Use when working with DynamoDB, adding data models, creating seed scripts, or implementing data access patterns"
---

# Skill: DynamoDB Data Operations

## Single-Table Design Pattern

This project uses a single DynamoDB table with composite keys:

| Entity | PK | SK | Example |
|--------|----|----|---------|
| Client | `CLIENT#<id>` | `PROFILE` | `CLIENT#CLT001` / `PROFILE` |
| Portfolio | `CLIENT#<id>` | `PORTFOLIO` | `CLIENT#CLT001` / `PORTFOLIO` |
| Holding | `CLIENT#<id>` | `HOLDING#<index>` | `CLIENT#CLT001` / `HOLDING#001` |

## Data Access Patterns

### Get a single item

```javascript
import { GetCommand } from '@aws-sdk/lib-dynamodb';

const getClient = async (clientId) => {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { PK: `CLIENT#${clientId}`, SK: 'PROFILE' },
  }));
  return result.Item;
};
```

### Query all items for an entity

```javascript
import { QueryCommand } from '@aws-sdk/lib-dynamodb';

const getPortfolioHoldings = async (clientId) => {
  const result = await docClient.send(new QueryCommand({
    TableName: TABLE_NAME,
    KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues: {
      ':pk': `CLIENT#${clientId}`,
      ':sk': 'HOLDING#',
    },
  }));
  return result.Items;
};
```

### Scan all clients

```javascript
import { ScanCommand } from '@aws-sdk/lib-dynamodb';

const listClients = async () => {
  const result = await docClient.send(new ScanCommand({
    TableName: TABLE_NAME,
    FilterExpression: 'SK = :sk',
    ExpressionAttributeValues: { ':sk': 'PROFILE' },
  }));
  return result.Items;
};
```

### Write items (seeding)

```javascript
import { BatchWriteCommand } from '@aws-sdk/lib-dynamodb';

const seedData = async (items) => {
  const requests = items.map(item => ({
    PutRequest: { Item: item },
  }));

  // BatchWrite supports max 25 items per call
  for (let i = 0; i < requests.length; i += 25) {
    await docClient.send(new BatchWriteCommand({
      RequestItems: { [TABLE_NAME]: requests.slice(i, i + 25) },
    }));
  }
};
```

## Seed Script Pattern

Create in `backend/scripts/seed.js`:

```javascript
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, BatchWriteCommand } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({ region: 'eu-west-1' });
const docClient = DynamoDBDocumentClient.from(client);
const TABLE_NAME = process.env.TABLE_NAME || 'ClientPortfolios-dev';

const clients = [
  { PK: 'CLIENT#CLT001', SK: 'PROFILE', name: 'Smith Family Trust', portfolioValue: 2450000, riskProfile: 'Balanced' },
  // ... more items
];

// Run seed
await seedData(clients);
console.log('Seed complete');
```

Add to package.json:
```json
"scripts": {
  "seed": "node scripts/seed.js"
}
```

## Table Definition (serverless.yml)

```yaml
resources:
  Resources:
    ClientPortfoliosTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:provider.environment.TABLE_NAME}
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: PK
            AttributeType: S
          - AttributeName: SK
            AttributeType: S
        KeySchema:
          - AttributeName: PK
            KeyType: HASH
          - AttributeName: SK
            KeyType: RANGE
```

## Checklist

- [ ] PK/SK follow the `ENTITY#id` / `SORT_KEY` pattern
- [ ] Use `PAY_PER_REQUEST` billing (no capacity planning for demos)
- [ ] BatchWrite respects 25-item limit per call
- [ ] Table name comes from environment variable
- [ ] No GSIs unless explicitly needed
- [ ] Scan operations include a FilterExpression to limit results
