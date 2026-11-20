import React, { useState, useEffect, useCallback } from 'react';
import AppLayout from '@cloudscape-design/components/app-layout';
import Header from './components/Header';
import RiskAlertsBanner from './components/RiskAlertsBanner';
import ClientListView from './components/ClientListView';
import PortfolioDetailView from './components/PortfolioDetailView';
import { fetchClients, fetchPortfolio } from './api/client';
import { computeRiskAlerts } from './utils/riskCalculations';

/**
 * Main App component.
 * Manages global state, fetches clients on mount, computes risk alerts,
 * and conditionally renders ClientListView or PortfolioDetailView.
 */
function App() {
  const [clients, setClients] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState(null);
  const [alerts, setAlerts] = useState([]);

  // Fetch all clients on mount
  useEffect(() => {
    async function loadClients() {
      try {
        const data = await fetchClients();
        setClients(data);
      } catch (err) {
        console.error('Failed to fetch clients:', err);
      }
    }
    loadClients();
  }, []);

  // Compute risk alerts when clients are loaded — fetch all portfolios
  useEffect(() => {
    if (clients.length === 0) return;

    async function loadAlertsData() {
      try {
        const portfolioMap = {};
        const results = await Promise.all(
          clients.map((client) => fetchPortfolio(client.id))
        );
        results.forEach((p, i) => {
          portfolioMap[clients[i].id] = p;
        });
        const computedAlerts = computeRiskAlerts(clients, portfolioMap);
        setAlerts(computedAlerts);
      } catch (err) {
        console.error('Failed to compute risk alerts:', err);
      }
    }
    loadAlertsData();
  }, [clients]);

  // Fetch portfolio when a client is selected
  useEffect(() => {
    if (!selectedClientId) {
      setPortfolio(null);
      setInsights(null);
      setInsightsError(null);
      return;
    }

    async function loadPortfolio() {
      try {
        const data = await fetchPortfolio(selectedClientId);
        setPortfolio(data);
      } catch (err) {
        console.error('Failed to fetch portfolio:', err);
        setPortfolio(null);
      }
    }
    loadPortfolio();
  }, [selectedClientId]);

  const handleSelectClient = useCallback((clientId) => {
    setSelectedClientId(clientId);
    setInsights(null);
    setInsightsError(null);
  }, []);

  const handleBackToList = useCallback(() => {
    setSelectedClientId(null);
  }, []);

  // Determine which view to render
  const renderContent = () => {
    if (selectedClientId) {
      return (
        <PortfolioDetailView
          clientId={selectedClientId}
          onBack={handleBackToList}
        />
      );
    }

    return (
      <ClientListView clients={clients} onSelectClient={handleSelectClient} />
    );
  };

  return (
    <>
      <Header />
      <AppLayout
        content={renderContent()}
        notifications={<RiskAlertsBanner alerts={alerts} />}
        navigationHide={true}
        toolsHide={true}
        headerSelector=".header-wrapper"
      />
    </>
  );
}

export default App;
