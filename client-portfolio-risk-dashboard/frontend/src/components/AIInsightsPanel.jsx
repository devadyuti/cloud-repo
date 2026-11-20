import React, { useState } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import Button from '@cloudscape-design/components/button';
import Spinner from '@cloudscape-design/components/spinner';
import Alert from '@cloudscape-design/components/alert';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Box from '@cloudscape-design/components/box';
import { generateInsights } from '../api/client';
import InsightCard from './InsightCard';

/**
 * AIInsightsPanel component.
 * Allows the user to request AI-generated rebalancing suggestions
 * from Amazon Bedrock and displays the results.
 *
 * @param {Object} props
 * @param {string} props.clientId - Client ID for the insights request
 * @param {Object} props.allocation - Current portfolio allocation
 * @param {string} props.riskProfile - Client's risk profile
 * @param {Object} props.riskMetrics - Current risk metrics
 */
function AIInsightsPanel({ clientId, allocation, riskProfile, riskMetrics }) {
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGetInsights = async () => {
    if (!allocation || !riskProfile) return;

    setLoading(true);
    setError(null);
    setSuggestions(null);

    try {
      const response = await generateInsights(clientId, {
        allocation,
        riskProfile,
        riskMetrics,
      });
      setSuggestions(response.suggestions);
    } catch (err) {
      setError(err.message || 'Failed to generate insights. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            <Button
              variant="primary"
              onClick={handleGetInsights}
              loading={loading}
              disabled={!allocation || !riskProfile}
            >
              Get AI Insights
            </Button>
          }
        >
          AI Rebalancing Insights
        </Header>
      }
    >
      <SpaceBetween size="m">
        {loading && (
          <Box textAlign="center" padding="l">
            <Spinner size="large" />
            <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>
              Generating AI insights…
            </Box>
          </Box>
        )}

        {error && (
          <Alert type="error" header="Insights Error">
            {error}
          </Alert>
        )}

        {suggestions && suggestions.length > 0 && (
          <SpaceBetween size="s">
            {suggestions.map((suggestion, index) => (
              <InsightCard key={index} suggestion={suggestion} index={index} />
            ))}
          </SpaceBetween>
        )}

        {!loading && !error && !suggestions && (
          <Box textAlign="center" color="text-body-secondary" padding="l">
            Click "Get AI Insights" to receive AI-powered rebalancing suggestions for this portfolio.
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
}

export default AIInsightsPanel;
