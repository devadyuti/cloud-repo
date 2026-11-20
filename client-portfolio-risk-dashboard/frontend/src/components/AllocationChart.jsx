import React from 'react';
import PieChart from '@cloudscape-design/components/pie-chart';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import Box from '@cloudscape-design/components/box';
import { formatPercentage } from '../utils/formatters';

/**
 * Segment colour palette for asset classes.
 */
const SEGMENT_COLOURS = {
  ukEquities: '#1B365D',
  internationalEquities: '#2E86AB',
  fixedIncome: '#4CAF50',
  alternatives: '#B8860B',
  cash: '#9E9E9E',
};

/**
 * Human-readable labels for allocation keys.
 */
const SEGMENT_LABELS = {
  ukEquities: 'UK Equities',
  internationalEquities: 'International Equities',
  fixedIncome: 'Fixed Income',
  alternatives: 'Alternatives',
  cash: 'Cash',
};

/**
 * AllocationChart component.
 * Renders a Cloudscape PieChart showing asset allocation breakdown.
 *
 * @param {Object} props
 * @param {Object} props.allocation - Allocation object with percentage values per asset class
 */
function AllocationChart({ allocation }) {
  if (!allocation) {
    return (
      <Container header={<Header variant="h2">Asset Allocation</Header>}>
        <Box textAlign="center" color="text-body-secondary" padding="l">
          No allocation data available.
        </Box>
      </Container>
    );
  }

  const data = Object.entries(SEGMENT_LABELS).map(([key, label]) => ({
    title: label,
    value: allocation[key] || 0,
    color: SEGMENT_COLOURS[key],
  }));

  return (
    <Container header={<Header variant="h2">Asset Allocation</Header>}>
      <PieChart
        data={data}
        detailPopoverContent={(datum) => [
          { key: 'Allocation', value: formatPercentage(datum.value, 1) },
        ]}
        segmentDescription={(datum) => `${formatPercentage(datum.value, 1)}`}
        size="medium"
        variant="donut"
        innerMetricDescription="total"
        innerMetricValue="100%"
        hideFilter
        empty={
          <Box textAlign="center" color="inherit">
            <b>No data</b>
          </Box>
        }
        noMatch={
          <Box textAlign="center" color="inherit">
            <b>No matching data</b>
          </Box>
        }
      />
    </Container>
  );
}

export default AllocationChart;
