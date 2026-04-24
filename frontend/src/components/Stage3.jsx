import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage3.css';

function ThinkingBlock({ thinking }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!thinking) return null;

  return (
    <div className="thinking-block">
      <div className="thinking-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="thinking-header-left">
          <svg className="thinking-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          <span className="thinking-label">CIO Reasoning</span>
        </div>
        <span className="thinking-toggle">
          {isExpanded ? 'COLLAPSE' : 'EXPAND'}
        </span>
      </div>
      {isExpanded && (
        <div className="thinking-content">
          {thinking}
        </div>
      )}
    </div>
  );
}

export default function Stage3({ finalResponse }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <div className="stage-header stage3-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="stage-title">
          <span className="stage-badge stage-badge-3">3</span>
          Chairman's Verdict
          <span className="cio-tag">FINAL</span>
        </h3>
        <button className="collapse-btn">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            {isCollapsed ? (
              <polyline points="9 18 15 12 9 6" />
            ) : (
              <polyline points="6 9 12 15 18 9" />
            )}
          </svg>
        </button>
      </div>

      {!isCollapsed && (
        <div className="stage-body stage3-body">
          <div className="cio-badge">
            <svg className="cio-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
            <div className="cio-info">
              <span className="cio-role">Chairman</span>
              <span className="cio-model">{finalResponse.model}</span>
            </div>
          </div>

          {/* CIO Thinking Block */}
          <ThinkingBlock thinking={finalResponse.thinking} />

          <div className="final-text markdown-content">
            <ReactMarkdown>
              {finalResponse.output || finalResponse.response}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
