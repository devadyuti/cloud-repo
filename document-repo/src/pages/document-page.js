import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { fetchDocument, DocumentNotFoundError } from '../services/document-service';
import MarkdownRenderer from '../components/markdown-renderer';
import LoadingIndicator from '../components/loading-indicator';
import ErrorDisplay from '../components/error-display';

function DocumentPage() {
  const location = useLocation();
  const path = location.pathname.replace(/^\//, '');

  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDocument = useCallback(async () => {
    setLoading(true);
    setError(null);
    setContent(null);

    try {
      const markdown = await fetchDocument(path);
      setContent(markdown);
    } catch (err) {
      if (err instanceof DocumentNotFoundError) {
        setError({ type: 'not-found', message: `Document not found: ${path}` });
      } else {
        setError({ type: 'network', message: err.message || 'Unable to load document' });
      }
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    loadDocument();
  }, [loadDocument]);

  useEffect(() => {
    if (content) {
      const headingMatch = content.match(/^#\s+(.+)$/m);
      if (headingMatch) {
        document.title = headingMatch[1];
      } else {
        const name = path.split('/').pop().replace(/-/g, ' ');
        document.title = name.charAt(0).toUpperCase() + name.slice(1);
      }
    } else {
      document.title = 'Loading...';
    }
    return () => { document.title = 'Docs'; };
  }, [content, path]);

  if (loading) {
    return (
      <div className="document-page">
        <LoadingIndicator />
      </div>
    );
  }

  if (error) {
    if (error.type === 'not-found') {
      return (
        <div className="document-page" role="alert">
          <h2>Document Not Found</h2>
          <p>The document at <code>{path}</code> could not be found.</p>
        </div>
      );
    }

    return (
      <div className="document-page">
        <ErrorDisplay message={error.message} onRetry={loadDocument} />
      </div>
    );
  }

  return (
    <div className="document-page">
      <MarkdownRenderer content={content} />
    </div>
  );
}

export default DocumentPage;
