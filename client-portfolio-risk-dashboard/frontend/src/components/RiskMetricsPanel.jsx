import React from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import ColumnLayout from '@cloudscape-design/components/column-layout';
import Box from '@cloudscape-design/components/box';

/**
 * RiskMetricsPanel component.
 * Displays four key risk metrics in a grid layout:
 * Volatility, Sharpe Ratio, Max Drawdown, and Beta vs FTSE 100.
 *
 * @param {Object} props
 * @param {Object} props.metrics - Risk metrics object
 * @param {number} props.metrics.volatility - Annualised volatility percentage
 * @param {number} props.metrics.sharpeRatio - Sharpe ratio decimal
 * @param {number} props.metrics.maxDrawdown - Max drawdown negative percentage
 * @param {number} props.metrics.betaFTSE100 - Beta vs FTSE 100 decimal
 */
function RiskMetricsPanel({ metrics }) {
  if (!metrics) {
    return (
      <Container header={<Header variant="h2">Risk Metrics</Header>}>
        <Box textAlign="center" color="text-body-secondary" padding="l">
          No risk metrics available.
        </Box>
      </Container>
    );
  }

  return (
    <Container header={<Header variant="h2">Risk Metrics</Header>}>
      <ColumnLayout columns={4} variant="text-grid">
        <div>
          <Box variant="awsui-key-label">Volatility</Box>
          <Box variant="awsui-value-large">{metrics.volatility}%</Box>
          <Box variant="small" color="text-body-secondary">Annualised</Box>
        </div>
        <div>
          <Box variant="awsui-key-label">Sharpe Ratio</Box>
          <Box variant="awsui-value-large">{metrics.sharpeRatio}</Box>
          <Box variant="small" color="text-body-secondary">Risk-adjusted return</Box>
        </div>
        <div>
          <Box variant="awsui-key-label">Max Drawdown</Box>
          <Box variant="awsui-value-large">{metrics.maxDrawdown}%</Box>
          <Box variant="small" color="text-body-secondary">12-month period</Box>
        </div>
        <div>
          <Box variant="awsui-key-label">Beta vs FTSE 100</Box>
          <Box variant="awsui-value-large">{metrics.betaFTSE100}</Box>
          <Box variant="small" color="text-body-secondary">Market sensitivity</Box>
        </div>
      </ColumnLayout>
    </Container>
  );
}

export default RiskMetricsPanel;
