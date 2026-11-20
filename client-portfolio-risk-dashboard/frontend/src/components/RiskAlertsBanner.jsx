import React from 'react';
import Flashbar from '@cloudscape-design/components/flashbar';

/**
 * RiskAlertsBanner component.
 * Displays warning banners for portfolios that breach risk thresholds.
 * Uses Cloudscape Flashbar with type "warning" for each alert.
 *
 * @param {{ alerts: Array<{ clientId: string, clientName: string, type: string, message: string }> }} props
 */
function RiskAlertsBanner({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return null;
  }

  const items = alerts.map((alert, index) => ({
    type: 'warning',
    dismissible: true,
    dismissLabel: 'Dismiss alert',
    content: alert.message,
    id: `${alert.clientId}-${alert.type}-${index}`,
  }));

  return <Flashbar items={items} />;
}

export default RiskAlertsBanner;
