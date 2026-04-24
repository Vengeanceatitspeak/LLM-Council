import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

/**
 * Rich markdown renderer with syntax highlighting, tables, and copy buttons.
 */
export default function MarkdownRenderer({ content }) {
  if (!content) return null;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const codeString = String(children).replace(/\n$/, '');

          if (!inline && match) {
            return (
              <CodeBlock language={match[1]} value={codeString} />
            );
          }

          if (!inline && codeString.includes('\n')) {
            return <CodeBlock language="text" value={codeString} />;
          }

          return (
            <code className="inline-code" {...props}>
              {children}
            </code>
          );
        },
        table({ children }) {
          return (
            <div className="table-wrapper">
              <table className="md-table">{children}</table>
            </div>
          );
        },
        thead({ children }) {
          return <thead className="md-thead">{children}</thead>;
        },
        th({ children }) {
          return <th className="md-th">{children}</th>;
        },
        td({ children }) {
          return <td className="md-td">{children}</td>;
        },
        a({ href, children }) {
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
              {children}
            </a>
          );
        },
        blockquote({ children }) {
          return <blockquote className="md-blockquote">{children}</blockquote>;
        },
        h1({ children }) { return <h1 className="md-h1">{children}</h1>; },
        h2({ children }) { return <h2 className="md-h2">{children}</h2>; },
        h3({ children }) { return <h3 className="md-h3">{children}</h3>; },
        ul({ children }) { return <ul className="md-ul">{children}</ul>; },
        ol({ children }) { return <ol className="md-ol">{children}</ol>; },
        li({ children }) { return <li className="md-li">{children}</li>; },
        p({ children }) { return <p className="md-p">{children}</p>; },
        strong({ children }) { return <strong className="md-strong">{children}</strong>; },
        hr() { return <hr className="md-hr" />; },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}


function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-language">{language}</span>
        <button className="copy-btn" onClick={handleCopy}>
          {copied ? (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: '0 0 8px 8px',
          fontSize: '13px',
          lineHeight: '1.5',
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
}
