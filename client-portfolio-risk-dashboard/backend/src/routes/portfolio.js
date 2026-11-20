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
 * GET /clients/{id}/portfolio — return a client's full portfolio data.
 * Lambda handler invoked directly by API Gateway HTTP API.
 */
export async function getPortfolio(event) {
  try {
    const id = event.pathParameters?.id;
    if (!id) {
      return jsonResponse(400, { error: 'Missing client ID' });
    }

    const portfolio = await db.getPortfolio(id);

    if (!portfolio) {
      return jsonResponse(404, { error: 'Portfolio not found', clientId: id });
    }

    return jsonResponse(200, portfolio);
  } catch (err) {
    console.error('getPortfolio error:', err);
    return jsonResponse(500, { error: 'Internal server error' });
  }
}
