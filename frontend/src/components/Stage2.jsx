import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function getDisplayName(model, rankings) {
  const match = rankings?.find((r) => r.model === model || r.display_name === model);
  return match?.display_name || model;
}

function deAnonymizeText(text, labelToModel, allRankings) {
  if (!labelToModel) return text;

  let result = text;
  Object.entries(labelToModel).forEach(([label, displayName]) => {
    result = result.replace(new RegExp(label, 'g'), `**${displayName}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  const getRankIndicator = (index) => {
    if (index === 0) return '#1';
    if (index === 1) return '#2';
    if (index === 2) return '#3';
    return `#${index + 1}`;
  };

  const getRankClass = (index) => {
    if (index === 0) return 'rank-gold';
    if (index === 1) return 'rank-silver';
    if (index === 2) return 'rank-bronze';
    return '';
  };

  return (
    <div className="stage stage2">
      <div className="stage-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="stage-title">
          <span className="stage-badge stage-badge-2">2</span>
          Peer Review &amp; Rankings
          <span className="stage-count">{rankings.length} reviewers</span>
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
          {/* Aggregate Rankings Leaderboard */}
          {aggregateRankings && aggregateRankings.length > 0 && (
            <div className="leaderboard">
              <h4 className="leaderboard-title">Performance Leaderboard</h4>
              <div className="leaderboard-list">
                {aggregateRankings.map((agg, index) => (
                  <div
                    key={index}
                    className={`leaderboard-item ${index < 3 ? 'top-three' : ''}`}
                  >
                    <span className={`leaderboard-rank ${getRankClass(index)}`}>
                      {getRankIndicator(index)}
                    </span>
                    <span className="leaderboard-name">
                      {agg.display_name || agg.model}
                    </span>
                    <div className="leaderboard-stats">
                      <span className="leaderboard-score">
                        {agg.average_rank.toFixed(2)}
                      </span>
                      <span className="leaderboard-votes">
                        {agg.rankings_count} votes
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <h4 className="evaluations-title">Raw Evaluations</h4>
          <p className="stage-description">
            Each model reviewed all analyses anonymously. Names shown below are for readability.
          </p>

          <div className="tabs">
            {rankings.map((rank, index) => (
              <button
                key={index}
                className={`tab ${activeTab === index ? 'active' : ''}`}
                onClick={() => setActiveTab(index)}
              >
                {rank.display_name || rank.model}
              </button>
            ))}
          </div>

          <div className="tab-content">
            <div className="ranking-model">
              {rankings[activeTab].display_name || rankings[activeTab].model}
            </div>
            <div className="ranking-content markdown-content">
              <ReactMarkdown>
                {deAnonymizeText(rankings[activeTab].ranking, labelToModel, rankings)}
              </ReactMarkdown>
            </div>

            {rankings[activeTab].parsed_ranking &&
             rankings[activeTab].parsed_ranking.length > 0 && (
              <div className="parsed-ranking">
                <strong>Extracted Ranking:</strong>
                <ol>
                  {rankings[activeTab].parsed_ranking.map((label, i) => (
                    <li key={i}>
                      <span className={`parsed-rank ${getRankClass(i)}`}>
                        {getRankIndicator(i)}
                      </span>
                      {labelToModel && labelToModel[label]
                        ? labelToModel[label]
                        : label}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
