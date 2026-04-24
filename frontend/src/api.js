/**
 * API client for MakeMeRichGPT backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Rename a conversation.
   */
  async renameConversation(conversationId, title) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to rename conversation');
    }
    return response.json();
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Get daily usage / credits with token tracking.
   */
  async getUsage() {
    const response = await fetch(`${API_BASE}/api/usage`);
    if (!response.ok) {
      throw new Error('Failed to get usage');
    }
    return response.json();
  },

  /**
   * Get council members info.
   */
  async getCouncilMembers() {
    const response = await fetch(`${API_BASE}/api/council/members`);
    if (!response.ok) {
      throw new Error('Failed to get council members');
    }
    return response.json();
  },

  /**
   * Upload a file to a conversation.
   */
  async uploadFile(conversationId, file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/upload`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) {
      throw new Error('Failed to upload file');
    }
    return response.json();
  },

  /**
   * Search the web.
   */
  async searchWeb(query, maxResults = 5) {
    const response = await fetch(`${API_BASE}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, max_results: maxResults }),
    });
    if (!response.ok) {
      throw new Error('Failed to search web');
    }
    return response.json();
  },

  /**
   * Scrape a URL.
   */
  async scrapeUrl(url) {
    const response = await fetch(`${API_BASE}/api/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) {
      throw new Error('Failed to scrape URL');
    }
    return response.json();
  },

  /**
   * Generate an image.
   */
  async generateImage(prompt) {
    const response = await fetch(`${API_BASE}/api/generate-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: prompt }),
    });
    if (!response.ok) {
      throw new Error('Failed to generate image');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      if (response.status === 429) {
        throw new Error('Daily credit limit reached. Please try again tomorrow.');
      }
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId
   * @param {string} content
   * @param {function} onEvent - Callback: (eventType, data) => void
   * @param {boolean} imageMode - Whether to generate images alongside text
   */
  async sendMessageStream(conversationId, content, onEvent, imageMode = false) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, image_mode: imageMode }),
      }
    );

    if (!response.ok) {
      if (response.status === 429) {
        throw new Error('Daily credit limit reached. Please try again tomorrow.');
      }
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      // Keep the last potentially incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }

    // Process any remaining buffer
    if (buffer.startsWith('data: ')) {
      try {
        const event = JSON.parse(buffer.slice(6));
        onEvent(event.type, event);
      } catch (e) {
        // ignore incomplete final chunk
      }
    }
  },
};
