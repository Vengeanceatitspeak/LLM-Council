import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage3.css';

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
          Chief Investment Officer's Verdict
          <span className="cio-tag">FINAL</span>
        </h3>
        <button className="collapse-btn">
          {isCollapsed ? '▸' : '▾'}
        </button>
      </div>

      {!isCollapsed && (
        <div className="stage-body stage3-body">
          <div className="cio-badge">
            <span className="cio-icon">👔</span>
            <div className="cio-info">
              <span className="cio-role">{finalResponse.role || 'Chief Investment Officer'}</span>
              <span className="cio-model">{finalResponse.model}</span>
            </div>
          </div>
          <div className="final-text markdown-content">
            <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
