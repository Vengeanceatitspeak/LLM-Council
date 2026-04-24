import { useState } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import './Stage1.css';

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
          <span className="thinking-label">Chain of Thought</span>
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

export default function Stage1({ responses, timing, tokens }) {
  const [activeTab, setActiveTab] = useState(0);
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <div className="stage-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="stage-title">
          <span className="stage-badge">1</span>
          Individual Model Analyses
          <span className="stage-count">{responses.length} models</span>
          {timing && <span className="stage-timing">{timing}s</span>}
          {tokens > 0 && <span className="stage-tokens">{tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : tokens} tok</span>}
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
        <div className="stage-body">
          <div className="tabs">
            {responses.map((resp, index) => (
              <button
                key={index}
                className={`tab ${activeTab === index ? 'active' : ''}`}
                onClick={() => setActiveTab(index)}
                style={{
                  '--tab-color': resp.color || '#888',
                }}
              >
                <span className="tab-dot" style={{ background: resp.color || '#888' }} />
                <span className="tab-label">
                  {resp.display_name || resp.model}
                </span>
              </button>
            ))}
          </div>

          <div className="tab-content">
            <div className="model-badge">
              <span className="model-dot" style={{ background: responses[activeTab].color }} />
              <div className="model-info">
                <span className="model-display-name">
                  {responses[activeTab].display_name || responses[activeTab].model}
                </span>
                <span className="model-name">{responses[activeTab].model}</span>
              </div>
              {responses[activeTab].tokens?.total_tokens > 0 && (
                <span className="model-tokens">
                  {responses[activeTab].tokens.total_tokens} tokens
                </span>
              )}
            </div>

            {/* Thinking Block — visible chain of thought */}
            <ThinkingBlock thinking={responses[activeTab].thinking} />

            <div className="response-text markdown-content">
              <MarkdownRenderer
                content={responses[activeTab].output || responses[activeTab].response}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
