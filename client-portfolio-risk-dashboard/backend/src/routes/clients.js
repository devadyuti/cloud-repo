import * as db from '../services/dynamodb.js';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
};

/**
 * Build a JSON response with CORS headers.
 */
function jsonResponse(statusCode, body) {
  return {
    statusCode,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    body: JSON.stringify(body)
  };
}

/**
 * GET /clients — return all clients.
 * Lambda handler invoked directly by API Gateway HTTP API.
 */
export async function listClients() {
  try {
    const clients = await db.getAllClients();
    return jsonResponse(200, clients);
  } catch (err) {
    console.error('listClients error:', err);
    return jsonResponse(500, { error: 'Internal server error' });
  }
}

/**
 * GET /clients/{id} — return a single client by ID.
 * Lambda handler invoked directly by API Gateway HTTP API.
 */
export async function getClient(event) {
  try {
    const id = event.pathParameters?.id;
    if (!id) {
      return jsonResponse(400, { error: 'Missing client ID' });
    }

    const client = await db.getClient(id);

    if (!client) {
      return jsonResponse(404, { error: 'Client not found', clientId: id });
    }

    return jsonResponse(200, client);
  } catch (err) {
    console.error('getClient error:', err);
    return jsonResponse(500, { error: 'Internal server error' });
  }
}
