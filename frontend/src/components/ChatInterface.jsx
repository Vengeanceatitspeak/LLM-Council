import { useState, useEffect, useRef } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

const SUGGESTED_PROMPTS = [
  { text: 'How should I structure my software engineering team?' },
  { text: 'Analyze the ethical implications of AI in healthcare.' },
  { text: 'What is the most plausible solution to the Fermi Paradox?' },
  { text: 'Design a 5-day workout split for hypertrophy.' },
  { text: 'How can we solve the housing affordability crisis?' },
  { text: 'Explain the difference between Keynesian and Austrian economics.' },
];

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${mins}m ${secs}s`;
}

function formatTokens(count) {
  if (!count) return '0';
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

function ThinkingTimerDisplay({ timer, active }) {
  return (
    <div className={`thinking-timer ${active ? 'active' : 'done'}`}>
      <div className="timer-icon-wrapper">
        <svg className={`timer-icon ${active ? 'spinning' : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      </div>
      <span className="timer-value">{timer.toFixed(1)}s</span>
      <span className="timer-label">{active ? 'thinking...' : 'total'}</span>
    </div>
  );
}

function FileChip({ file, onRemove }) {
  const getFileIcon = (type) => {
    switch (type) {
      case 'pdf':
        return (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        );
      case 'image':
        return (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        );
      default:
        return (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
          </svg>
        );
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="file-chip">
      <span className="file-chip-icon">{getFileIcon(file.file_type)}</span>
      <span className="file-chip-name">{file.filename}</span>
      {file.size_bytes && <span className="file-chip-size">{formatSize(file.size_bytes)}</span>}
      {onRemove && (
        <button className="file-chip-remove" onClick={onRemove} type="button">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
}

function GeneratedImage({ imageData }) {
  const [enlarged, setEnlarged] = useState(false);

  if (!imageData) return null;
  if (imageData.error) {
    return (
      <div className="image-gen-error">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        <span>{imageData.error}</span>
      </div>
    );
  }

  const imgSrc = `data:image/png;base64,${imageData.image_base64}`;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = imgSrc;
    link.download = imageData.filename || 'generated-image.png';
    link.click();
  };

  return (
    <div className="generated-image-container">
      <div className="gen-image-header">
        <span className="gen-image-label">Generated Image</span>
        {imageData.duration_sec && (
          <span className="gen-image-duration">{imageData.duration_sec}s</span>
        )}
      </div>
      <div className={`gen-image-wrapper ${enlarged ? 'enlarged' : ''}`}>
        <img
          src={imgSrc}
          alt={imageData.prompt || 'Generated image'}
          className="gen-image"
          onClick={() => setEnlarged(!enlarged)}
        />
      </div>
      <div className="gen-image-actions">
        <button className="gen-image-btn" onClick={() => setEnlarged(!enlarged)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 3 21 3 21 9" />
            <polyline points="9 21 3 21 3 15" />
            <line x1="21" y1="3" x2="14" y2="10" />
            <line x1="3" y1="21" x2="10" y2="14" />
          </svg>
          {enlarged ? 'Shrink' : 'Enlarge'}
        </button>
        <button className="gen-image-btn" onClick={handleDownload}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download
        </button>
      </div>
      {imageData.prompt && (
        <div className="gen-image-prompt">Prompt: "{imageData.prompt}"</div>
      )}
    </div>
  );
}

function TimingBadge({ timing }) {
  if (!timing) return null;
  const hasTiming = timing.stage1 || timing.stage2 || timing.stage3 || timing.total;
  if (!hasTiming) return null;

  return (
    <div className="timing-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <div className="timing-details">
        {timing.stage1 && <span>S1: {formatDuration(timing.stage1)}</span>}
        {timing.stage2 && <span>S2: {formatDuration(timing.stage2)}</span>}
        {timing.stage3 && <span>S3: {formatDuration(timing.stage3)}</span>}
        {timing.total && <span className="timing-total">Total: {formatDuration(timing.total)}</span>}
        {timing.totalTokens > 0 && <span className="timing-tokens">{formatTokens(timing.totalTokens)} tokens</span>}
      </div>
    </div>
  );
}

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  councilMembers,
  imageMode,
  onToggleImageMode,
  thinkingTimer,
  timerActive,
  onFileUpload,
  uploadedFiles,
  onRemoveFile,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

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

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      await onFileUpload(files[i]);
    }
    // Reset input so same file can be uploaded again
    e.target.value = '';
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
            <h1 className="welcome-title">CouncilGPT</h1>
            <p className="welcome-subtitle">
              Multi-Agent Expert Council
              <br />
              AI models analyze your queries through a 3-stage deliberation pipeline.
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
            <p>Submit a query to the expert council</p>

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
                      <MarkdownRenderer content={msg.content} />
                    </div>
                    {msg.files && msg.files.length > 0 && (
                      <div className="message-files">
                        {msg.files.map((f, fi) => (
                          <FileChip key={fi} file={f} />
                        ))}
                      </div>
                    )}
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
                    <div className="council-label-row">
                      <span className="council-label">Council Deliberation</span>
                      {/* Show thinking timer when loading */}
                      {(msg.loading?.stage1 || msg.loading?.stage2 || msg.loading?.stage3) && (
                        <ThinkingTimerDisplay timer={thinkingTimer} active={timerActive} />
                      )}
                      {/* Show final timing after complete */}
                      {msg.timing?.total && (
                        <TimingBadge timing={msg.timing} />
                      )}
                    </div>

                    {/* Web Scrape indicator — step-by-step display */}
                    {msg.loading?.webScrape && (
                      <div className="tool-step-card">
                        <div className="tool-step-header">
                          <div className="tool-step-spinner" />
                          <span className="tool-step-title">Scraping web pages</span>
                        </div>
                        <div className="tool-step-details">
                          {(msg.webScrapeData?.urls || []).map((url, i) => (
                            <div key={i} className="tool-step-item">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <line x1="2" y1="12" x2="22" y2="12" />
                                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                              </svg>
                              <span className="tool-step-url">{url.length > 60 ? url.substring(0, 60) + '...' : url}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {msg.webScrapeData && !msg.loading?.webScrape && (
                      <div className="tool-step-card completed">
                        <div className="tool-step-header">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          <span className="tool-step-title">Scraped {msg.webScrapeData?.urls?.length || 0} page(s)</span>
                          {msg.webScrapeData.duration_sec && <span className="tool-step-duration">{msg.webScrapeData.duration_sec}s</span>}
                        </div>
                      </div>
                    )}

                    {/* Web Search indicator — step-by-step display */}
                    {msg.loading?.webSearch && (
                      <div className="tool-step-card">
                        <div className="tool-step-header">
                          <div className="tool-step-spinner" />
                          <span className="tool-step-title">Searching the web for real-time data</span>
                        </div>
                        <div className="tool-step-details">
                          <div className="tool-step-item">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <circle cx="11" cy="11" r="8" />
                              <line x1="21" y1="21" x2="16.65" y2="16.65" />
                            </svg>
                            <span className="tool-step-url">Querying DuckDuckGo...</span>
                          </div>
                        </div>
                      </div>
                    )}
                    {msg.webSearchData && !msg.loading?.webSearch && (
                      <div className="tool-step-card completed">
                        <div className="tool-step-header">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="11" cy="11" r="8" />
                            <line x1="21" y1="21" x2="16.65" y2="16.65" />
                          </svg>
                          <span className="tool-step-title">Found {msg.webSearchData.count} results</span>
                          {msg.webSearchData.duration_sec && <span className="tool-step-duration">{msg.webSearchData.duration_sec}s</span>}
                        </div>
                      </div>
                    )}

                    {/* Image Generation indicator */}
                    {msg.loading?.imageGen && (
                      <div className="tool-step-card image-gen">
                        <div className="tool-step-header">
                          <div className="tool-step-spinner" />
                          <span className="tool-step-title">Generating image via Cloudflare AI</span>
                        </div>
                        <div className="tool-step-details">
                          <div className="tool-step-item">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                              <circle cx="8.5" cy="8.5" r="1.5" />
                              <polyline points="21 15 16 10 5 21" />
                            </svg>
                            <span className="tool-step-url">Running FLUX.1 [schnell] model...</span>
                          </div>
                        </div>
                      </div>
                    )}
                    {msg.generatedImage && <GeneratedImage imageData={msg.generatedImage} />}

                    {/* Stage 1 */}
                    {msg.loading?.stage1 && (
                      <div className="stage-loading">
                        <div className="stage-loading-bar">
                          <div className="loading-pulse" />
                        </div>
                        <span>Stage 1: Consulting 10 models...</span>
                      </div>
                    )}
                    {msg.stage1 && <Stage1 responses={msg.stage1} timing={msg.timing?.stage1} tokens={msg.timing?.stage1_tokens} />}

                    {/* Stage 2 */}
                    {msg.loading?.stage2 && (
                      <div className="stage-loading">
                        <div className="stage-loading-bar">
                          <div className="loading-pulse" />
                        </div>
                        <span>Stage 2: Peer-reviewing analyses...</span>
                      </div>
                    )}
                    {msg.stage2 && (
                      <Stage2
                        rankings={msg.stage2}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateRankings={msg.metadata?.aggregate_rankings}
                        timing={msg.timing?.stage2}
                        tokens={msg.timing?.stage2_tokens}
                      />
                    )}

                    {/* Stage 3 */}
                    {msg.loading?.stage3 && (
                      <div className="stage-loading">
                        <div className="stage-loading-bar">
                          <div className="loading-pulse" />
                        </div>
                        <span>Stage 3: Synthesizing final verdict...</span>
                      </div>
                    )}
                    {msg.stage3 && <Stage3 finalResponse={msg.stage3} timing={msg.timing?.stage3} tokens={msg.timing?.stage3_tokens} />}
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
        {/* Uploaded file chips */}
        {uploadedFiles && uploadedFiles.length > 0 && (
          <div className="upload-chips-bar">
            {uploadedFiles.map((file, i) => (
              <FileChip key={i} file={file} onRemove={() => onRemoveFile(i)} />
            ))}
          </div>
        )}

        <div className="input-wrapper">
          {/* File upload button */}
          <button
            type="button"
            className="input-action-btn file-upload-btn"
            onClick={handleFileClick}
            title="Upload file (PDF, Image, Text)"
            disabled={isLoading || !conversation}
            id="file-upload-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            className="file-input-hidden"
            onChange={handleFileChange}
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp,.txt,.md,.csv,.log,.json,.xml,.html"
          />

          <textarea
            className="message-input"
            placeholder={isLoading ? 'Council is deliberating...' : 'Enter your query... (Enter to submit)'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            id="message-input"
          />

          <button
            type="button"
            className={`image-mode-toggle-btn ${imageMode ? 'active' : ''}`}
            onClick={onToggleImageMode}
            title={imageMode ? 'Image mode ON — will generate an image with response' : 'Enable image generation'}
            disabled={isLoading}
            id="image-mode-toggle"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <span className="image-mode-label">Create image</span>
          </button>

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

        {/* Status bar under input */}
        <div className="input-status-bar">
          {imageMode && <span className="status-tag image-tag">Image Mode</span>}
          {isLoading && (
            <span className="status-tag thinking-tag">
              <div className="mini-spinner" />
              Thinking {thinkingTimer.toFixed(1)}s
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
