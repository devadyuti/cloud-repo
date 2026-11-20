import React from 'react';
import Table from '@cloudscape-design/components/table';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import Link from '@cloudscape-design/components/link';
import Badge from '@cloudscape-design/components/badge';
import Box from '@cloudscape-design/components/box';
import { formatCurrency, formatDate } from '../utils/formatters';

/**
 * Maps risk profile to a Cloudscape Badge colour.
 * @param {"Conservative"|"Balanced"|"Growth"} riskProfile
 * @returns {"blue"|"green"|"red"}
 */
function getBadgeColor(riskProfile) {
  switch (riskProfile) {
    case 'Conservative':
      return 'blue';
    case 'Balanced':
      return 'green';
    case 'Growth':
      return 'red';
    default:
      return 'grey';
  }
}

/**
 * Column definitions for the client table.
 */
const COLUMN_DEFINITIONS = [
  {
    id: 'name',
    header: 'Client Name',
    cell: (item) => item._nameLink,
    sortingField: 'name',
  },
  {
    id: 'portfolioValue',
    header: 'Portfolio Value',
    cell: (item) => formatCurrency(item.portfolioValue),
    sortingField: 'portfolioValue',
  },
  {
    id: 'riskProfile',
    header: 'Risk Profile',
    cell: (item) => <Badge color={getBadgeColor(item.riskProfile)}>{item.riskProfile}</Badge>,
    sortingField: 'riskProfile',
  },
  {
    id: 'lastReviewDate',
    header: 'Last Review Date',
    cell: (item) => formatDate(item.lastReviewDate),
    sortingField: 'lastReviewDate',
  },
];

/**
 * ClientListView component.
 * Displays all clients in a Cloudscape Table with clickable names.
 *
 * @param {Object} props
 * @param {Array} props.clients - Array of client objects
 * @param {Function} props.onSelectClient - Callback when a client is selected (receives client ID)
 */
function ClientListView({ clients, onSelectClient }) {
  // Enrich items with a clickable Link element for the name column
  const items = clients.map((client) => ({
    ...client,
    _nameLink: (
      <Link
        onFollow={(e) => {
          e.preventDefault();
          onSelectClient(client.id);
        }}
        href="#"
      >
        {client.name}
      </Link>
    ),
  }));

  return (
    <Container header={<Header variant="h2">Client Portfolios</Header>}>
      <Table
        columnDefinitions={COLUMN_DEFINITIONS}
        items={items}
        variant="embedded"
        stripedRows
        empty={
          <Box textAlign="center" color="inherit" padding="l">
            <b>No clients</b>
            <Box variant="p" color="inherit">
              No client data available.
            </Box>
          </Box>
        }
      />
    </Container>
  );
}

export default ClientListView;
