/**
 * Risk calculation utilities for the Client Portfolio Risk Dashboard.
 * Evaluates portfolios against risk thresholds and generates alert objects.
 */

/**
 * Target asset allocations per risk profile (percentages).
 * Must stay in sync with backend/src/services/bedrock.js TARGET_ALLOCATIONS.
 */
export const TARGET_ALLOCATIONS = {
  Conservative: { ukEquities: 20, internationalEquities: 15, fixedIncome: 40, alternatives: 10, cash: 15 },
  Balanced: { ukEquities: 30, internationalEquities: 25, fixedIncome: 25, alternatives: 12, cash: 8 },
  Growth: { ukEquities: 40, internationalEquities: 30, fixedIncome: 15, alternatives: 10, cash: 5 },
};

/**
 * Maximum acceptable annualised volatility per risk profile.
 */
export const VOLATILITY_TARGETS = {
  Conservative: 8,
  Balanced: 12,
  Growth: 18,
};

/**
 * Threshold (in percentage points) above target equity allocation that triggers an alert.
 */
const EQUITY_OVERWEIGHT_THRESHOLD = 10;

/**
 * Compute risk alerts for all clients by evaluating portfolios against thresholds.
 *
 * Checks two conditions:
 * 1. Equity overweight — total equity allocation (UK + International) exceeds the
 *    target for the client's risk profile by more than 10 percentage points.
 * 2. Volatility breach — portfolio annualised volatility exceeds the target for
 *    the client's risk profile.
 *
 * @param {Array<{id: string, name: string, riskProfile: string}>} clients
 * @param {Object<string, {allocation: object, riskMetrics: object}>} portfolios
 *   A map of clientId → portfolio data
 * @returns {Array<{clientId: string, clientName: string, type: string, message: string}>}
 */
export function computeRiskAlerts(clients, portfolios) {
  const alerts = [];

  for (const client of clients) {
    const portfolio = portfolios[client.id];
    if (!portfolio) continue;

    const { allocation, riskMetrics } = portfolio;
    const riskProfile = client.riskProfile;
    const target = TARGET_ALLOCATIONS[riskProfile];

    if (!target || !allocation || !riskMetrics) continue;

    // Check equity overweight
    const totalEquity = (allocation.ukEquities || 0) + (allocation.internationalEquities || 0);
    const targetEquity = (target.ukEquities || 0) + (target.internationalEquities || 0);
    const equityDiff = totalEquity - targetEquity;

    if (equityDiff > EQUITY_OVERWEIGHT_THRESHOLD) {
      alerts.push({
        clientId: client.id,
        clientName: client.name,
        type: 'equity_overweight',
        message: `${client.name} — equity allocation (${totalEquity}%) exceeds target (${targetEquity}%) by ${equityDiff.toFixed(1)}pp`,
      });
    }

    // Check volatility breach
    const volatilityTarget = VOLATILITY_TARGETS[riskProfile];
    if (volatilityTarget != null && riskMetrics.volatility > volatilityTarget) {
      alerts.push({
        clientId: client.id,
        clientName: client.name,
        type: 'volatility_breach',
        message: `${client.name} — portfolio volatility (${riskMetrics.volatility}%) exceeds ${riskProfile} target (${volatilityTarget}%)`,
      });
    }
  }

  return alerts;
}
