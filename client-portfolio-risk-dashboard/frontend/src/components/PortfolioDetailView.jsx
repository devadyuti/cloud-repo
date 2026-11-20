import React, { useState, useEffect } from 'react';
import ContentLayout from '@cloudscape-design/components/content-layout';
import Header from '@cloudscape-design/components/header';
import BreadcrumbGroup from '@cloudscape-design/components/breadcrumb-group';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Grid from '@cloudscape-design/components/grid';
import Spinner from '@cloudscape-design/components/spinner';
import Box from '@cloudscape-design/components/box';
import { fetchClient, fetchPortfolio } from '../api/client';
import AllocationChart from './AllocationChart';
import HoldingsTable from './HoldingsTable';
import RiskMetricsPanel from './RiskMetricsPanel';
import AIInsightsPanel from './AIInsightsPanel';

/**
 * PortfolioDetailView component.
 * Displays a single client's portfolio: allocation chart, holdings table,
 * risk metrics, and AI insights panel.
 *
 * @param {Object} props
 * @param {string} props.clientId - The selected client's ID
 * @param {Function} props.onBack - Callback to navigate back to client list
 */
function PortfolioDetailView({ clientId, onBack }) {
  const [client, setClient] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [clientData, portfolioData] = await Promise.all([
          fetchClient(clientId),
          fetchPortfolio(clientId),
        ]);
        if (!cancelled) {
          setClient(clientData);
          setPortfolio(portfolioData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load portfolio data.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadData();
    return () => { cancelled = true; };
  }, [clientId]);

  if (loading) {
    return (
      <Box textAlign="center" padding="xxl">
        <Spinner size="large" />
        <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>
          Loading portfolio data…
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box textAlign="center" padding="xxl">
        <Box variant="h3" color="text-status-error">Error</Box>
        <Box variant="p">{error}</Box>
      </Box>
    );
  }

  const clientName = client?.name || 'Client';

  return (
    <ContentLayout
      header={
        <Header variant="h1">{clientName}</Header>
      }
    >
      <SpaceBetween size="l">
        <BreadcrumbGroup
          items={[
            { text: 'Clients', href: '#' },
            { text: clientName, href: '#' },
          ]}
          onFollow={(e) => {
            e.preventDefault();
            if (e.detail.href === '#' && e.detail.text === 'Clients') {
              onBack();
            }
          }}
        />

        <Grid
          gridDefinition={[
            { colspan: { default: 12, m: 6 } },
            { colspan: { default: 12, m: 6 } },
          ]}
        >
          <AllocationChart allocation={portfolio?.allocation} />
          <RiskMetricsPanel metrics={portfolio?.riskMetrics} />
        </Grid>

        <HoldingsTable holdings={portfolio?.holdings} />

        <AIInsightsPanel
          clientId={clientId}
          allocation={portfolio?.allocation}
          riskProfile={client?.riskProfile}
          riskMetrics={portfolio?.riskMetrics}
        />
      </SpaceBetween>
    </ContentLayout>
  );
}

export default PortfolioDetailView;
