import React from 'react';

function LoadingIndicator() {
  return (
    <div className="loading-indicator" role="status" aria-label="Loading document">
      <div className="spinner" aria-hidden="true" />
      <p>Loading...</p>
    </div>
  );
}

export default LoadingIndicator;
