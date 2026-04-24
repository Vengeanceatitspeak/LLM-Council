import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [usage, setUsage] = useState({
    used: 0, limit: 50, remaining: 50, percentage: 0,
    tokens_used: 0, tokens_limit: 500000, tokens_remaining: 500000, tokens_percentage: 0,
  });
  const [councilMembers, setCouncilMembers] = useState([]);
  const [imageMode, setImageMode] = useState(false);
  const [stageTiming, setStageTiming] = useState({});
  const [thinkingTimer, setThinkingTimer] = useState(0);
  const [timerActive, setTimerActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // Load conversations, usage, and council members on mount
  useEffect(() => {
    loadConversations();
    loadUsage();
    loadCouncilMembers();
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
      // Reset uploads when switching conversations
      setUploadedFiles([]);
    }
  }, [currentConversationId]);

  // Thinking timer — counts up every 100ms while active
  useEffect(() => {
    let interval = null;
    if (timerActive) {
      interval = setInterval(() => {
        setThinkingTimer((prev) => prev + 0.1);
      }, 100);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [timerActive]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadUsage = async () => {
    try {
      const u = await api.getUsage();
      setUsage(u);
    } catch (error) {
      console.error('Failed to load usage:', error);
    }
  };

  const loadCouncilMembers = async () => {
    try {
      const data = await api.getCouncilMembers();
      setCouncilMembers(data.members || []);
    } catch (error) {
      console.error('Failed to load council members:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, title: 'New Conversation', message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await api.renameConversation(id, newTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
      if (currentConversation && currentConversation.id === id) {
        setCurrentConversation((prev) => ({ ...prev, title: newTitle }));
      }
    } catch (error) {
      console.error('Failed to rename conversation:', error);
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleFileUpload = async (file) => {
    if (!currentConversationId) return;
    try {
      const result = await api.uploadFile(currentConversationId, file);
      setUploadedFiles((prev) => [...prev, {
        filename: result.filename,
        file_type: result.file_type,
        size_bytes: result.size_bytes,
      }]);
      return result;
    } catch (error) {
      console.error('Failed to upload file:', error);
      return null;
    }
  };

  const handleRemoveFile = (index) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    // Check credits
    if (usage.remaining <= 0) {
      alert('Daily credit limit reached. Please try again tomorrow.');
      return;
    }

    setIsLoading(true);
    setThinkingTimer(0);
    setTimerActive(true);
    setStageTiming({});

    try {
      // Optimistically add user message to UI (include file info)
      const userMessage = {
        role: 'user',
        content,
        files: uploadedFiles.length > 0 ? [...uploadedFiles] : undefined,
      };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Clear uploaded files after sending
      setUploadedFiles([]);

      // Create a partial assistant message
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        generatedImage: null,
        webScrapeData: null,
        webSearchData: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
          imageGen: false,
          webScrape: false,
          webSearch: false,
        },
        timing: {},
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'usage_update':
            setUsage(event.data);
            break;

          case 'web_scrape_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, webScrape: true };
              lastMsg.webScrapeData = { urls: event.data?.urls || [] };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'web_scrape_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, webScrape: false };
              if (lastMsg.webScrapeData) {
                lastMsg.webScrapeData.duration_sec = event.data?.duration_sec;
              }
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'web_search_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, webSearch: true };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'web_search_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, webSearch: false };
              lastMsg.webSearchData = {
                count: event.data?.count || 0,
                duration_sec: event.data?.duration_sec,
              };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'image_gen_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, imageGen: true };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'image_gen_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, imageGen: false };
              lastMsg.generatedImage = {
                image_base64: event.data?.image_base64,
                filename: event.data?.filename,
                prompt: event.data?.prompt,
                duration_sec: event.data?.duration_sec,
              };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'image_gen_error':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, imageGen: false };
              lastMsg.generatedImage = { error: event.data?.message || 'Image generation failed' };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, stage1: true };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setStageTiming((prev) => ({ ...prev, stage1: event.timing?.duration_sec }));
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.stage1 = event.data;
              lastMsg.loading = { ...lastMsg.loading, stage1: false };
              lastMsg.timing = { ...lastMsg.timing, stage1: event.timing?.duration_sec, stage1_tokens: event.timing?.tokens };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, stage2: true };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setStageTiming((prev) => ({ ...prev, stage2: event.timing?.duration_sec }));
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading = { ...lastMsg.loading, stage2: false };
              lastMsg.timing = { ...lastMsg.timing, stage2: event.timing?.duration_sec, stage2_tokens: event.timing?.tokens };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.loading = { ...lastMsg.loading, stage3: true };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setStageTiming((prev) => ({ ...prev, stage3: event.timing?.duration_sec }));
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.stage3 = event.data;
              lastMsg.loading = { ...lastMsg.loading, stage3: false };
              lastMsg.timing = { ...lastMsg.timing, stage3: event.timing?.duration_sec, stage3_tokens: event.timing?.tokens };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            setConversations((prev) =>
              prev.map((c) =>
                c.id === currentConversationId
                  ? { ...c, title: event.data.title }
                  : c
              )
            );
            setCurrentConversation((prev) => ({
              ...prev,
              title: event.data.title,
            }));
            break;

          case 'complete':
            setStageTiming((prev) => ({
              ...prev,
              total: event.data?.total_duration_sec,
              totalTokens: event.data?.total_tokens,
            }));
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = { ...messages[messages.length - 1] };
              lastMsg.timing = {
                ...lastMsg.timing,
                total: event.data?.total_duration_sec,
                totalTokens: event.data?.total_tokens,
              };
              messages[messages.length - 1] = lastMsg;
              return { ...prev, messages };
            });
            loadConversations();
            loadUsage();
            setIsLoading(false);
            setTimerActive(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            setTimerActive(false);
            break;

          default:
            break;
        }
      }, imageMode);
    } catch (error) {
      console.error('Failed to send message:', error);
      if (error.message.includes('credit limit')) {
        alert(error.message);
      }
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
      setTimerActive(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        usage={usage}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        councilMembers={councilMembers}
        imageMode={imageMode}
        onToggleImageMode={() => setImageMode(!imageMode)}
        thinkingTimer={thinkingTimer}
        timerActive={timerActive}
        onFileUpload={handleFileUpload}
        uploadedFiles={uploadedFiles}
        onRemoveFile={handleRemoveFile}
      />
    </div>
  );
}

export default App;
