import React from 'react';

function ErrorDisplay({ message, onRetry }) {
  return (
    <div className="error-display" role="alert">
      <h2>Error</h2>
      <p>{message}</p>
      {onRetry && (
        <button onClick={onRetry}>Retry</button>
      )}
    </div>
  );
}

export default ErrorDisplay;
