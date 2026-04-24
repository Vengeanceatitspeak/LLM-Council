import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
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
          Individual Specialist Analyses
          <span className="stage-count">{responses.length} specialists</span>
        </h3>
        <button className="collapse-btn">
          {isCollapsed ? '▸' : '▾'}
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
                <span className="tab-icon">{resp.icon || '💼'}</span>
                <span className="tab-label">{resp.role || resp.model.split('/')[1] || resp.model}</span>
              </button>
            ))}
          </div>

          <div className="tab-content">
            <div className="model-badge">
              <span className="model-icon">{responses[activeTab].icon || '💼'}</span>
              <div className="model-info">
                <span className="model-role" style={{ color: responses[activeTab].color }}>
                  {responses[activeTab].role || 'Analyst'}
                </span>
                <span className="model-name">{responses[activeTab].model}</span>
              </div>
            </div>
            <div className="response-text markdown-content">
              <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
