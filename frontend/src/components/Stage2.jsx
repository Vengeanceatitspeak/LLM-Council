import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

// Map model to role info
function getRoleInfo(model, rankings) {
  const match = rankings?.find((r) => r.model === model);
  return match?.role || model.split('/')[1] || model;
}

function deAnonymizeText(text, labelToModel, allRankings) {
  if (!labelToModel) return text;

  let result = text;
  Object.entries(labelToModel).forEach(([label, model]) => {
    const role = allRankings
      ? getRoleInfo(model, allRankings)
      : model.split('/')[1] || model;
    result = result.replace(new RegExp(label, 'g'), `**${role}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  const getMedalIcon = (index) => {
    if (index === 0) return '🥇';
    if (index === 1) return '🥈';
    if (index === 2) return '🥉';
    return `#${index + 1}`;
  };

  return (
    <div className="stage stage2">
      <div className="stage-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="stage-title">
          <span className="stage-badge stage-badge-2">2</span>
          Peer Review & Rankings
          <span className="stage-count">{rankings.length} reviewers</span>
        </h3>
        <button className="collapse-btn">
          {isCollapsed ? '▸' : '▾'}
        </button>
      </div>

      {!isCollapsed && (
        <div className="stage-body">
          {/* Aggregate Rankings Leaderboard */}
          {aggregateRankings && aggregateRankings.length > 0 && (
            <div className="leaderboard">
              <h4 className="leaderboard-title">📊 Performance Leaderboard</h4>
              <div className="leaderboard-list">
                {aggregateRankings.map((agg, index) => (
                  <div
                    key={index}
                    className={`leaderboard-item ${index < 3 ? 'top-three' : ''}`}
                  >
                    <span className="leaderboard-medal">{getMedalIcon(index)}</span>
                    <span className="leaderboard-role">
                      {agg.role || agg.model.split('/')[1] || agg.model}
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
            Each specialist reviewed all analyses anonymously. Role names shown below are for readability.
          </p>

          <div className="tabs">
            {rankings.map((rank, index) => (
              <button
                key={index}
                className={`tab ${activeTab === index ? 'active' : ''}`}
                onClick={() => setActiveTab(index)}
              >
                {rank.role || rank.model.split('/')[1] || rank.model}
              </button>
            ))}
          </div>

          <div className="tab-content">
            <div className="ranking-model">
              {rankings[activeTab].role || rankings[activeTab].model}
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
                      <span className="parsed-medal">{getMedalIcon(i)}</span>
                      {labelToModel && labelToModel[label]
                        ? getRoleInfo(labelToModel[label], rankings)
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
