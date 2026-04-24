import { useState } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  usage,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  const handleStartRename = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title || 'New Conversation');
  };

  const handleSaveRename = (id) => {
    if (editTitle.trim()) {
      onRenameConversation(id, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleRenameKeyDown = (e, id) => {
    if (e.key === 'Enter') {
      handleSaveRename(id);
    } else if (e.key === 'Escape') {
      setEditingId(null);
      setEditTitle('');
    }
  };

  const handleDeleteClick = (e, id) => {
    e.stopPropagation();
    setDeleteConfirmId(id);
  };

  const handleConfirmDelete = (e, id) => {
    e.stopPropagation();
    onDeleteConversation(id);
    setDeleteConfirmId(null);
  };

  const handleCancelDelete = (e) => {
    e.stopPropagation();
    setDeleteConfirmId(null);
  };

  // Credit bar color based on usage
  const getUsageColor = () => {
    if (usage.percentage < 50) return 'var(--accent-green)';
    if (usage.percentage < 80) return 'var(--accent-gold)';
    return 'var(--accent-red)';
  };

  const getUsageGradient = () => {
    if (usage.percentage < 50) return 'linear-gradient(90deg, #00d4aa, #00b894)';
    if (usage.percentage < 80) return 'linear-gradient(90deg, #f59e0b, #f97316)';
    return 'linear-gradient(90deg, #ef4444, #dc2626)';
  };

  return (
    <div className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand">
          <span className="brand-icon">💰</span>
          <div className="brand-text">
            <h1>MakeMeRichGPT</h1>
            <span className="brand-subtitle">Finance AI Council</span>
          </div>
        </div>
        <button
          className="new-conversation-btn"
          onClick={onNewConversation}
          title="New Conversation"
          id="new-conversation-btn"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Credit Usage Bar */}
      <div className="credit-section">
        <div className="credit-header">
          <span className="credit-label">Daily Credits</span>
          <span className="credit-count" style={{ color: getUsageColor() }}>
            {usage.used}/{usage.limit}
          </span>
        </div>
        <div className="credit-bar-track">
          <div
            className="credit-bar-fill"
            style={{
              width: `${usage.percentage}%`,
              background: getUsageGradient(),
            }}
          />
        </div>
        <span className="credit-remaining">
          {usage.remaining > 0
            ? `${usage.remaining} queries remaining`
            : 'Daily limit reached — resets at midnight UTC'}
        </span>
      </div>

      {/* Conversation List */}
      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">
            <span className="no-conv-icon">💬</span>
            <span>No conversations yet</span>
            <span className="no-conv-hint">Start a new chat to begin</span>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
              id={`conv-${conv.id.slice(0, 8)}`}
            >
              {editingId === conv.id ? (
                <input
                  className="rename-input"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => handleRenameKeyDown(e, conv.id)}
                  onBlur={() => handleSaveRename(conv.id)}
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : deleteConfirmId === conv.id ? (
                <div className="delete-confirm" onClick={(e) => e.stopPropagation()}>
                  <span className="delete-confirm-text">Delete this chat?</span>
                  <div className="delete-confirm-actions">
                    <button
                      className="delete-yes"
                      onClick={(e) => handleConfirmDelete(e, conv.id)}
                    >
                      Yes
                    </button>
                    <button
                      className="delete-no"
                      onClick={handleCancelDelete}
                    >
                      No
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="conversation-title">
                    {conv.title || 'New Conversation'}
                  </div>
                  <div className="conversation-actions">
                    <button
                      className="action-btn rename-btn"
                      onClick={(e) => handleStartRename(e, conv)}
                      title="Rename"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                    </button>
                    <button
                      className="action-btn delete-btn"
                      onClick={(e) => handleDeleteClick(e, conv.id)}
                      title="Delete"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <span>10 AI Specialists • 3-Stage Analysis</span>
      </div>
    </div>
  );
}
