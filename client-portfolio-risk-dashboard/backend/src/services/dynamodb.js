import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, ScanCommand } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({ region: 'eu-west-1' });
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = process.env.TABLE_NAME;

/**
 * Get all client profiles from the table.
 * Uses a Scan with a filter on SK = 'PROFILE'.
 * @returns {Promise<import('../../scripts/seed.js').Client[]>}
 */
export async function getAllClients() {
  const result = await docClient.send(
    new ScanCommand({
      TableName: TABLE_NAME,
      FilterExpression: 'SK = :sk',
      ExpressionAttributeValues: { ':sk': 'PROFILE' }
    })
  );

  return (result.Items || []).map(stripKeys);
}

/**
 * Get a single client profile by ID.
 * @param {string} id - Client ID (e.g., "CLT001")
 * @returns {Promise<object|null>}
 */
export async function getClient(id) {
  const result = await docClient.send(
    new GetCommand({
      TableName: TABLE_NAME,
      Key: { PK: `CLIENT#${id}`, SK: 'PROFILE' }
    })
  );

  return result.Item ? stripKeys(result.Item) : null;
}

/**
 * Get a client's portfolio data by ID.
 * @param {string} id - Client ID (e.g., "CLT001")
 * @returns {Promise<object|null>}
 */
export async function getPortfolio(id) {
  const result = await docClient.send(
    new GetCommand({
      TableName: TABLE_NAME,
      Key: { PK: `CLIENT#${id}`, SK: 'PORTFOLIO' }
    })
  );

  return result.Item ? stripKeys(result.Item) : null;
}

/**
 * Remove DynamoDB key attributes (PK, SK) from the returned item
 * so the API response only contains domain fields.
 */
function stripKeys(item) {
  const { PK, SK, ...rest } = item;
  return rest;
}
