/**
 * API client module for the Client Portfolio Risk Dashboard.
 * Uses AWS Amplify REST API to communicate with the backend Lambda API via API Gateway.
 */

import { get, post } from 'aws-amplify/api';

const API_NAME = 'PortfolioAPI';

/**
 * Fetch all clients.
 * GET /clients → array of client objects
 * @returns {Promise<import('../types/models').Client[]>}
 */
export async function fetchClients() {
  const { body } = await get({ apiName: API_NAME, path: '/clients' }).response;
  return body.json();
}

/**
 * Fetch a single client by ID.
 * GET /clients/{id} → client object
 * @param {string} id - Client ID (e.g., "CLT001")
 * @returns {Promise<import('../types/models').Client>}
 */
export async function fetchClient(id) {
  const { body } = await get({ apiName: API_NAME, path: `/clients/${id}` }).response;
  return body.json();
}

/**
 * Fetch a client's portfolio data.
 * GET /clients/{id}/portfolio → portfolio object
 * @param {string} id - Client ID (e.g., "CLT001")
 * @returns {Promise<import('../types/models').Portfolio>}
 */
export async function fetchPortfolio(id) {
  const { body } = await get({ apiName: API_NAME, path: `/clients/${id}/portfolio` }).response;
  return body.json();
}

/**
 * Generate AI rebalancing insights for a client's portfolio.
 * POST /clients/{id}/insights → insights response
 * @param {string} id - Client ID (e.g., "CLT001")
 * @param {import('../types/models').InsightsRequest} requestBody - Allocation, risk profile, and metrics
 * @returns {Promise<import('../types/models').InsightsResponse>}
 */
export async function generateInsights(id, requestBody) {
  const { body } = await post({
    apiName: API_NAME,
    path: `/clients/${id}/insights`,
    options: {
      body: requestBody,
    },
  }).response;
  return body.json();
}
