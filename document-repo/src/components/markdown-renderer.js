import React, { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { github } from 'react-syntax-highlighter/dist/cjs/styles/hljs';

const copyButtonStyle = {
  position: 'absolute',
  top: '8px',
  right: '8px',
  padding: '4px 8px',
  fontSize: '12px',
  color: '#57606a',
  backgroundColor: '#f6f8fa',
  border: '1px solid #d0d7de',
  borderRadius: '4px',
  cursor: 'pointer',
  lineHeight: 1,
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);
  return (
    <button style={copyButtonStyle} onClick={handleCopy} aria-label="Copy code">
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

const markdownStyles = {
  container: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    lineHeight: 1.6,
    color: '#24292e',
    wordWrap: 'break-word',
  },
  h1: { fontSize: '2em', fontWeight: 600, borderBottom: '1px solid #eaecef', paddingBottom: '0.3em', marginTop: '1.5em', marginBottom: '0.5em' },
  h2: { fontSize: '1.5em', fontWeight: 600, borderBottom: '1px solid #eaecef', paddingBottom: '0.3em', marginTop: '1.5em', marginBottom: '0.5em' },
  h3: { fontSize: '1.25em', fontWeight: 600, marginTop: '1.5em', marginBottom: '0.5em' },
  h4: { fontSize: '1em', fontWeight: 600, marginTop: '1.5em', marginBottom: '0.5em' },
  h5: { fontSize: '0.875em', fontWeight: 600, marginTop: '1.5em', marginBottom: '0.5em' },
  h6: { fontSize: '0.85em', fontWeight: 600, color: '#6a737d', marginTop: '1.5em', marginBottom: '0.5em' },
  p: { marginTop: '0', marginBottom: '16px' },
  blockquote: {
    margin: '0 0 16px 0',
    padding: '0 1em',
    color: '#6a737d',
    borderLeft: '0.25em solid #dfe2e5',
  },
  table: { borderCollapse: 'collapse', width: '100%', marginBottom: '16px' },
  th: { fontWeight: 600, padding: '6px 13px', border: '1px solid #dfe2e5', backgroundColor: '#f6f8fa' },
  td: { padding: '6px 13px', border: '1px solid #dfe2e5' },
  code: {
    fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
    fontSize: '85%',
    backgroundColor: 'rgba(27,31,35,0.05)',
    borderRadius: '3px',
    padding: '0.2em 0.4em',
  },
  pre: { marginBottom: '16px', borderRadius: '6px', overflow: 'auto' },
  img: { maxWidth: '100%', height: 'auto' },
  hr: { height: '0.25em', padding: 0, margin: '24px 0', backgroundColor: '#e1e4e8', border: 0 },
  a: { color: '#0366d6', textDecoration: 'none' },
  ul: { paddingLeft: '2em', marginBottom: '16px' },
  ol: { paddingLeft: '2em', marginBottom: '16px' },
  li: { marginBottom: '4px' },
};

const rendererComponents = {
  h1: ({ children }) => <h1 style={markdownStyles.h1}>{children}</h1>,
  h2: ({ children }) => <h2 style={markdownStyles.h2}>{children}</h2>,
  h3: ({ children }) => <h3 style={markdownStyles.h3}>{children}</h3>,
  h4: ({ children }) => <h4 style={markdownStyles.h4}>{children}</h4>,
  h5: ({ children }) => <h5 style={markdownStyles.h5}>{children}</h5>,
  h6: ({ children }) => <h6 style={markdownStyles.h6}>{children}</h6>,
  p: ({ children }) => <p style={markdownStyles.p}>{children}</p>,
  blockquote: ({ children }) => <blockquote style={markdownStyles.blockquote}>{children}</blockquote>,
  table: ({ children }) => <table style={markdownStyles.table}>{children}</table>,
  th: ({ children }) => <th style={markdownStyles.th}>{children}</th>,
  td: ({ children }) => <td style={markdownStyles.td}>{children}</td>,
  img: ({ src, alt }) => <img src={src} alt={alt || ''} style={markdownStyles.img} />,
  hr: () => <hr style={markdownStyles.hr} />,
  a: ({ href, children }) => <a href={href} style={markdownStyles.a}>{children}</a>,
  ul: ({ children }) => <ul style={markdownStyles.ul}>{children}</ul>,
  ol: ({ children }) => <ol style={markdownStyles.ol}>{children}</ol>,
  li: ({ children }) => <li style={markdownStyles.li}>{children}</li>,
  code: ({ className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '');
    const codeString = String(children).replace(/\n$/, '');

    if (match) {
      return (
        <div style={{ position: 'relative' }}>
          <CopyButton text={codeString} />
          <SyntaxHighlighter
            style={github}
            language={match[1]}
            PreTag="div"
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      );
    }

    return <code style={markdownStyles.code} {...props}>{children}</code>;
  },
  pre: ({ children }) => <pre style={markdownStyles.pre}>{children}</pre>,
};

function MarkdownRenderer({ content }) {
  return (
    <div style={markdownStyles.container} className="markdown-renderer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={rendererComponents}
      >
        {content || ''}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownRenderer;
