import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import '@cloudscape-design/global-styles/index.css';
import './index.css';
import App from './App';

Amplify.configure({
  API: {
    REST: {
      PortfolioAPI: {
        endpoint: process.env.REACT_APP_API_URL || '',
        region: 'eu-west-1',
      },
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
