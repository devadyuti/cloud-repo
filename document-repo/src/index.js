import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import { amplifyConfig, validateConfig } from './amplify-config';
import App from './app';
import './styles/global.css';

const root = ReactDOM.createRoot(document.getElementById('root'));

try {
  validateConfig(amplifyConfig);
  Amplify.configure(amplifyConfig);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
} catch (error) {
  root.render(
    <div role="alert" style={{ padding: '2rem', color: '#d32f2f', fontFamily: 'sans-serif' }}>
      <h1>Configuration Error</h1>
      <p>{error.message}</p>
    </div>
  );
}
