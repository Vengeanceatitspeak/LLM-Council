import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

const SUGGESTED_PROMPTS = [
  { text: 'Should I buy NVIDIA at current levels?' },
  { text: 'Best options strategy for earnings season?' },
  { text: 'How will Fed rate cuts impact my portfolio?' },
  { text: 'Is Bitcoin a good hedge against inflation?' },
  { text: 'Best growth ETFs for a 10-year horizon?' },
  { text: 'How to hedge my tech-heavy portfolio?' },
];

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  councilMembers,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestionClick = (text) => {
    if (!isLoading) {
      onSendMessage(text);
    }
  };

  // Welcome screen — no conversation selected
  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="welcome-screen">
          <div className="welcome-content">
            <div className="welcome-logo">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="welcome-title">MakeMeRichGPT</h1>
            <p className="welcome-subtitle">
              Financial Deliberation Council
              <br />
              10 AI models analyze your queries through a 3-stage LangGraph pipeline.
            </p>

            {councilMembers && councilMembers.length > 0 && (
              <div className="council-roster">
                {councilMembers.map((member, i) => (
                  <div
                    key={i}
                    className="roster-chip"
                    style={{ borderColor: member.color + '30' }}
                  >
                    <span className="roster-dot" style={{ background: member.color }} />
                    <span className="roster-name">{member.display_name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" opacity="0.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h2>Start a Session</h2>
            <p>Submit a financial query to the deliberation council</p>

            <div className="suggestions-grid">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  className="suggestion-card"
                  onClick={() => handleSuggestionClick(prompt.text)}
                  disabled={isLoading}
                  id={`suggestion-${i}`}
                >
                  <svg className="suggestion-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                  <span className="suggestion-text">{prompt.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group" style={{ animationDelay: `${index * 50}ms` }}>
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-avatar user-avatar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-avatar council-avatar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <div className="message-content council-content">
                    <div className="council-label">Council Deliberation</div>

                    {/* Stage 1 */}
                    {msg.loading?.stage1 && (
                      <div className="stage-loading">
                        <div className="stage-loading-bar">
                          <div className="loading-pulse"></div>
                        </div>
                        <span>Stage 1: Consulting 10 models...</span>
                      </div>
                    )}
                    {msg.stage1 && <Stage1 responses={msg.stage1} />}

                    {/* Stage 2 */}
                    {msg.loading?.stage2 && (
                      <div className="stage-loading">
                        <div className="stage-loading-bar">
                          <div className="loading-pulse"></div>
                        </div>
                        <span>Stage 2: Peer-reviewing analyses...</span>
                      </div>
                    )}
                    {msg.stage2 && (
                      <Stage2
                        rankings={msg.stage2}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateRankings={msg.metadata?.aggregate_rankings}
                      />
                    )}

                    {/* Stage 3 */}
                    {msg.loading?.stage3 && (
                      <div className="stage-loading">
                        <div className="stage-loading-bar">
                          <div className="loading-pulse"></div>
                        </div>
                        <span>Stage 3: Synthesizing final verdict...</span>
                      </div>
                    )}
                    {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form className="input-form" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <textarea
            className="message-input"
            placeholder="Enter your financial query... (Enter to submit)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            id="message-input"
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
            id="send-button"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
