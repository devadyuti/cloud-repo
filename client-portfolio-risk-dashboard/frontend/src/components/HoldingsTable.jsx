import React, { useMemo } from 'react';
import Table from '@cloudscape-design/components/table';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import StatusIndicator from '@cloudscape-design/components/status-indicator';
import Box from '@cloudscape-design/components/box';
import { formatCurrency, formatPercentage } from '../utils/formatters';

/**
 * Column definitions for the holdings table.
 */
const COLUMN_DEFINITIONS = [
  {
    id: 'name',
    header: 'Name',
    cell: (item) => item.name,
    sortingField: 'name',
  },
  {
    id: 'sector',
    header: 'Sector',
    cell: (item) => item.sector,
    sortingField: 'sector',
  },
  {
    id: 'value',
    header: 'Value (GBP)',
    cell: (item) => formatCurrency(item.value),
    sortingField: 'value',
  },
  {
    id: 'weight',
    header: 'Weight (%)',
    cell: (item) => formatPercentage(item.weight, 1),
    sortingField: 'weight',
  },
  {
    id: 'change1M',
    header: '1M Change (%)',
    cell: (item) => {
      const value = item.change1M;
      if (value > 0) {
        return (
          <StatusIndicator type="success">
            +{formatPercentage(value, 1)}
          </StatusIndicator>
        );
      }
      if (value < 0) {
        return (
          <StatusIndicator type="error">
            {formatPercentage(value, 1)}
          </StatusIndicator>
        );
      }
      return formatPercentage(value, 1);
    },
    sortingField: 'change1M',
  },
];

/**
 * HoldingsTable component.
 * Displays a client's top holdings sorted by weight in descending order.
 *
 * @param {Object} props
 * @param {Array} props.holdings - Array of holding objects
 */
function HoldingsTable({ holdings }) {
  const sortedHoldings = useMemo(() => {
    if (!holdings || holdings.length === 0) return [];
    return [...holdings].sort((a, b) => b.weight - a.weight);
  }, [holdings]);

  return (
    <Container header={<Header variant="h2">Top Holdings</Header>}>
      <Table
        columnDefinitions={COLUMN_DEFINITIONS}
        items={sortedHoldings}
        variant="embedded"
        stripedRows
        sortingColumn={COLUMN_DEFINITIONS[3]}
        sortingDescending={true}
        empty={
          <Box textAlign="center" color="inherit" padding="l">
            <b>No holdings</b>
            <Box variant="p" color="inherit">
              No holdings data available.
            </Box>
          </Box>
        }
      />
    </Container>
  );
}

export default HoldingsTable;
