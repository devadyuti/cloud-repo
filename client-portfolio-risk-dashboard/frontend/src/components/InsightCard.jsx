import React from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import Box from '@cloudscape-design/components/box';

/**
 * InsightCard component.
 * Displays a single AI-generated rebalancing suggestion with a gold accent border.
 *
 * @param {Object} props
 * @param {string} props.suggestion - The suggestion text
 * @param {number} props.index - Zero-based index of the suggestion
 */
function InsightCard({ suggestion, index }) {
  return (
    <div className="insight-card-accent">
      <Container
        header={<Header variant="h3">Suggestion {index + 1}</Header>}
      >
        <Box variant="p">{suggestion}</Box>
      </Container>
    </div>
  );
}

export default InsightCard;
