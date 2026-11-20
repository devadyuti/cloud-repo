import { generateInsights as callBedrock } from '../services/bedrock.js';

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
 * POST /clients/{id}/insights — generate AI rebalancing suggestions.
 * Lambda handler invoked directly by API Gateway HTTP API.
 * Expects request body with allocation, riskProfile, and riskMetrics.
 */
export async function generateInsights(event) {
  try {
    const id = event.pathParameters?.id;
    if (!id) {
      return jsonResponse(400, { error: 'Missing client ID' });
    }

    const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;
    const { allocation, riskProfile, riskMetrics } = body || {};

    if (!allocation || !riskProfile || !riskMetrics) {
      return jsonResponse(400, {
        error: 'Request body must include allocation, riskProfile, and riskMetrics'
      });
    }

    const suggestions = await callBedrock(allocation, riskProfile, riskMetrics);
    return jsonResponse(200, { suggestions });
  } catch (err) {
    console.error('generateInsights error:', err);
    return jsonResponse(500, { error: 'Failed to generate insights. Please try again.' });
  }
}
