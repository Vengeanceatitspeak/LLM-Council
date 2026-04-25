import { useState, useEffect } from 'react';
import './CouncilSettings.css';

const API_BASE = 'http://localhost:8001';

const AVAILABLE_MODELS = [
  { id: 'llama-3.3-70b-versatile', label: 'LLaMA 3.3 70B Versatile' },
  { id: 'meta-llama/llama-4-scout-17b-16e-instruct', label: 'LLaMA 4 Scout 17B' },
  { id: 'qwen/qwen3-32b', label: 'Qwen 3 32B' },
  { id: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B' },
  { id: 'openai/gpt-oss-20b', label: 'GPT-OSS 20B' },
  { id: 'llama-3.1-8b-instant', label: 'LLaMA 3.1 8B Instant' },
  { id: 'allam-2-7b', label: 'Allam 2 7B' },
  { id: 'groq/compound', label: 'Groq Compound' },
  { id: 'groq/compound-mini', label: 'Groq Compound Mini' },
];

const AGENT_COLORS = [
  '#3b82f6', '#8b5cf6', '#06b6d4', '#ef4444', '#f59e0b',
  '#10b981', '#f97316', '#6366f1', '#ec4899', '#14b8a6',
];

function ModelSelect({ value, onChange }) {
  return (
    <select value={value} onChange={onChange} className="model-select">
      {AVAILABLE_MODELS.map(m => (
        <option key={m.id} value={m.id}>{m.label}</option>
      ))}
    </select>
  );
}

export default function CouncilSettings({ isOpen, onClose }) {
  const [settings, setSettings] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [activeTab, setActiveTab] = useState('agents');
  const [expandedAgent, setExpandedAgent] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
      setSuccessMsg('');
      setError('');
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/api/settings/council`);
      if (!response.ok) throw new Error('Failed to load settings');
      const data = await response.json();
      setSettings(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError('');
    setSuccessMsg('');
    try {
      const response = await fetch(`${API_BASE}/api/settings/council`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (!response.ok) throw new Error('Failed to save settings');
      setSuccessMsg('Saved!');
      setTimeout(() => { setSuccessMsg(''); onClose(); }, 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const updateMember = (index, field, value) => {
    const newMembers = [...settings.members];
    newMembers[index] = { ...newMembers[index], [field]: value };
    setSettings({ ...settings, members: newMembers });
  };

  const addMember = () => {
    const idx = settings.members.length;
    const newMember = {
      id: `agent_${Date.now()}`,
      role: 'New Agent',
      system_prompt: '',
      model: settings.default_model || 'llama-3.3-70b-versatile',
      temperature: 0.7,
      color: AGENT_COLORS[idx % AGENT_COLORS.length],
    };
    setSettings({ ...settings, members: [...settings.members, newMember] });
    setExpandedAgent(idx);
  };

  const removeMember = (index) => {
    if (settings.members.length <= 1) return;
    const newMembers = settings.members.filter((_, i) => i !== index);
    setSettings({ ...settings, members: newMembers });
    if (expandedAgent === index) setExpandedAgent(null);
    else if (expandedAgent > index) setExpandedAgent(expandedAgent - 1);
  };

  const duplicateMember = (index) => {
    const src = settings.members[index];
    const newMember = {
      ...src,
      id: `agent_${Date.now()}`,
      role: `${src.role} (Copy)`,
      color: AGENT_COLORS[(settings.members.length) % AGENT_COLORS.length],
    };
    const newMembers = [...settings.members];
    newMembers.splice(index + 1, 0, newMember);
    setSettings({ ...settings, members: newMembers });
    setExpandedAgent(index + 1);
  };

  if (!isOpen) return null;

  const promptPreview = (prompt) => {
    if (!prompt) return 'Using default system prompt';
    const clean = prompt.replace(/\s+/g, ' ').trim();
    return clean.length > 80 ? clean.substring(0, 80) + '…' : clean;
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-header">
          <div className="settings-header-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            <h2>Council Configuration</h2>
          </div>
          <button className="settings-close-btn" onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="settings-tabs">
          <button className={`settings-tab ${activeTab === 'agents' ? 'active' : ''}`} onClick={() => setActiveTab('agents')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            Agents
            {settings && <span className="tab-badge">{settings.members.length}</span>}
          </button>
          <button className={`settings-tab ${activeTab === 'pipeline' ? 'active' : ''}`} onClick={() => setActiveTab('pipeline')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Pipeline
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="settings-state"><div className="settings-spinner" /><span>Loading...</span></div>
        ) : error && !settings ? (
          <div className="settings-state error"><span>{error}</span><button className="retry-btn" onClick={loadSettings}>Retry</button></div>
        ) : settings ? (
          <div className="settings-body">

            {/* ─── AGENTS TAB ─── */}
            {activeTab === 'agents' && (
              <div className="agents-tab">
                {/* Default model for all agents */}
                <div className="default-model-row">
                  <label>Default Model (used by all agents)</label>
                  <ModelSelect
                    value={settings.default_model || 'llama-3.3-70b-versatile'}
                    onChange={(e) => setSettings({...settings, default_model: e.target.value})}
                  />
                </div>

                <div className="agents-toolbar">
                  <span className="agents-count">{settings.members.length} agent{settings.members.length !== 1 ? 's' : ''}</span>
                  <button className="add-agent-btn" onClick={addMember}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    Add Agent
                  </button>
                </div>

                <div className="agents-grid">
                  {settings.members.map((member, index) => (
                    <div key={member.id || index} className={`agent-card ${expandedAgent === index ? 'expanded' : ''}`}>
                      <div className="agent-card-summary" onClick={() => setExpandedAgent(expandedAgent === index ? null : index)}>
                        <div className="agent-identity">
                          <div className="agent-color-dot" style={{ background: member.color }} />
                          <div className="agent-info">
                            <span className="agent-role">{member.role || `Agent ${index + 1}`}</span>
                            <span className="agent-prompt-preview">{promptPreview(member.system_prompt)}</span>
                          </div>
                        </div>
                        <div className="agent-card-actions">
                          <button className="agent-action-btn" onClick={(e) => { e.stopPropagation(); duplicateMember(index); }} title="Duplicate">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                            </svg>
                          </button>
                          {settings.members.length > 1 && (
                            <button className="agent-action-btn danger" onClick={(e) => { e.stopPropagation(); removeMember(index); }} title="Remove">
                              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              </svg>
                            </button>
                          )}
                          <svg className={`expand-chevron ${expandedAgent === index ? 'rotated' : ''}`} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="6 9 12 15 18 9" />
                          </svg>
                        </div>
                      </div>

                      {expandedAgent === index && (
                        <div className="agent-card-details">
                          <div className="detail-row">
                            <div className="detail-field flex-2">
                              <label>Role Name</label>
                              <input type="text" value={member.role || ''} onChange={(e) => updateMember(index, 'role', e.target.value)} placeholder="e.g. Risk Analyst, Code Reviewer..." />
                            </div>
                            <div className="detail-field flex-0">
                              <label>Color</label>
                              <input type="color" value={member.color} onChange={(e) => updateMember(index, 'color', e.target.value)} className="color-input" />
                            </div>
                          </div>
                          <div className="detail-field">
                            <label>System Prompt <span className="optional-tag">optional — leave blank for default</span></label>
                            <textarea rows={4} value={member.system_prompt || ''} onChange={(e) => updateMember(index, 'system_prompt', e.target.value)} placeholder="Custom instructions for this agent's behavior..." />
                          </div>
                          <details className="advanced-toggle">
                            <summary>Advanced</summary>
                            <div className="detail-row" style={{marginTop: '12px'}}>
                              <div className="detail-field flex-2">
                                <label>Model Override</label>
                                <ModelSelect value={member.model || settings.default_model || 'llama-3.3-70b-versatile'} onChange={(e) => updateMember(index, 'model', e.target.value)} />
                              </div>
                              <div className="detail-field flex-1">
                                <label>Temperature</label>
                                <div className="temp-control">
                                  <input type="range" min="0" max="2" step="0.1" value={member.temperature || 0.7} onChange={(e) => updateMember(index, 'temperature', parseFloat(e.target.value))} className="temp-slider" />
                                  <span className="temp-value">{(member.temperature || 0.7).toFixed(1)}</span>
                                </div>
                              </div>
                            </div>
                          </details>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ─── PIPELINE TAB ─── */}
            {activeTab === 'pipeline' && (
              <div className="pipeline-tab">
                <div className="pipeline-stage">
                  <div className="stage-header">
                    <div className="stage-number">1</div>
                    <div className="stage-info">
                      <h4>Chairman — Task Decomposition</h4>
                      <p>Breaks the query into sub-tasks and assigns roles to agents</p>
                    </div>
                  </div>
                  <div className="stage-config">
                    <div className="detail-field">
                      <label>Model</label>
                      <ModelSelect value={settings.chairman_model} onChange={(e) => setSettings({...settings, chairman_model: e.target.value})} />
                    </div>
                    <div className="detail-field">
                      <label>System Prompt</label>
                      <textarea rows={5} value={settings.chairman_prompt} onChange={(e) => setSettings({...settings, chairman_prompt: e.target.value})} />
                    </div>
                  </div>
                </div>

                <div className="pipeline-connector">
                  <svg width="2" height="32"><line x1="1" y1="0" x2="1" y2="32" stroke="rgba(255,255,255,0.1)" strokeWidth="2" strokeDasharray="4 4"/></svg>
                </div>

                <div className="pipeline-stage">
                  <div className="stage-header">
                    <div className="stage-number">2</div>
                    <div className="stage-info">
                      <h4>Agents — Parallel Analysis</h4>
                      <p>Each agent executes its assigned sub-task independently</p>
                    </div>
                  </div>
                  <div className="stage-config muted">
                    <p className="stage-note">→ Configure agents in the "Agents" tab</p>
                  </div>
                </div>

                <div className="pipeline-connector">
                  <svg width="2" height="32"><line x1="1" y1="0" x2="1" y2="32" stroke="rgba(255,255,255,0.1)" strokeWidth="2" strokeDasharray="4 4"/></svg>
                </div>

                <div className="pipeline-stage">
                  <div className="stage-header">
                    <div className="stage-number">3</div>
                    <div className="stage-info">
                      <h4>Lead Synthesizer — Final Verdict</h4>
                      <p>Consolidates all outputs into one authoritative conclusion</p>
                    </div>
                  </div>
                  <div className="stage-config">
                    <div className="detail-field">
                      <label>Model</label>
                      <ModelSelect value={settings.synthesizer_model} onChange={(e) => setSettings({...settings, synthesizer_model: e.target.value})} />
                    </div>
                    <div className="detail-field">
                      <label>System Prompt</label>
                      <textarea rows={5} value={settings.synthesizer_prompt} onChange={(e) => setSettings({...settings, synthesizer_prompt: e.target.value})} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : null}

        {/* Footer */}
        <div className="settings-footer">
          {error && settings && <span className="footer-error">{error}</span>}
          {successMsg && <span className="footer-success">{successMsg}</span>}
          <div className="footer-actions">
            <button className="btn-secondary" onClick={onClose} disabled={isSaving}>Cancel</button>
            <button className="btn-primary" onClick={handleSave} disabled={isSaving || isLoading}>
              {isSaving ? <><div className="btn-spinner" />Saving...</> : <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                Save
              </>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
