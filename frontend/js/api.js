const getBase = () => {
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isLocal ? 'http://127.0.0.1:8000/api/v1' : (window.LEVI_CONFIG?.getApiBase() || '/api/v1');
};

const API_BASE = getBase();
window.API_BASE = API_BASE; // Sink to global for non-module access

const ui = {
    showLoader: () => {
        const l = document.getElementById('global-loader');
        if (l) { l.style.width = '30%'; l.style.opacity = '1'; }
    },
    finishLoader: () => {
        const l = document.getElementById('global-loader');
        if (l) { 
            l.style.width = '100%';
            setTimeout(() => { l.style.opacity = '0'; setTimeout(() => l.style.width = '0', 300); }, 200);
        }
    }
};

async function apiFetch(endpoint, options = {}) {
  ui.showLoader();
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  
  const defaultOptions = {
    headers: { "Content-Type": "application/json" },
  };

  const finalOptions = { ...defaultOptions, ...options };
  if (options.body && typeof options.body !== 'string') {
    finalOptions.body = JSON.stringify(options.body);
  }

  try {
    const res = await fetch(url, finalOptions);
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const errorMessage = errorData.error || errorData.detail || `Server Error: ${res.status}`;
        
        // Specific handling for standard codes
        if (res.status === 402 || errorData.error_code === "INSUFFICIENT_CREDITS") {
            throw new Error("PRO_UPGRADE_REQUIRED");
        }
        if (errorData.error_code === "RATE_LIMIT_EXCEEDED") {
            throw new Error("You are moving too fast. Deep breaths! Please wait a moment.");
        }
        
        throw new Error(errorMessage);
    }
    return await res.json();
  } catch (error) {
    console.error(`[LEVI] API Error (${endpoint}):`, error);
    const toast = (window.ui && window.ui.showToast) || window.showToast;
    if (toast) toast(error.message, "error");
    throw error;
  } finally {
    ui.finishLoader();
  }
}

// --- Dynamic Features (Orchestrator Integrated) ---

/**
 * SSE Chat Stream handler for the new LEVI Orchestrator.
 */
async function chatStream(message, sessionId, onChunk, onMetadata) {
    const url = `${API_BASE}/chat`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify({ message, session_id: sessionId, stream: true })
    });

    if (!response.ok) throw new Error(`Stream start failed: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let partial = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        partial += decoder.decode(value, { stream: true });
        const lines = partial.split('\n');
        partial = lines.pop(); // Keep last incomplete line

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6).trim();
                if (data === '[DONE]') break;
                try {
                    const json = JSON.parse(data);
                    if (json.metadata && Object.keys(json.metadata).length > 0) {
                        onMetadata(json.metadata);
                    }
                    if (json.choices?.[0]?.delta?.content) {
                        onChunk(json.choices[0].delta.content);
                    }
                } catch (e) {
                    console.warn("[LEVI] Malformed SSE chunk:", data);
                }
            }
        }
    }
}

// --- Legacy & Wrapped Methods ---
export const api = {
    chat: (message, session_id) => apiFetch("/chat", { method: "POST", body: { message, session_id } }),
    chatStream,
    getProfile: () => apiFetch("/auth/me"),
    getCredits: () => apiFetch("/auth/me"), // Synced to /auth/me for efficiency
    generateImage: (text, author, mood) => apiFetch("/studio/generate_image", { method: "POST", body: { text, author, mood } }),
    getTaskStatus: (taskId) => apiFetch(`/studio/task_status/${taskId}`),
    getFeed: (limit = 20) => apiFetch(`/gallery/feed?limit=${limit}`),
    getMyGallery: () => apiFetch("/gallery/my_gallery"),
    likeItem: (type, id) => apiFetch(`/gallery/like/${type}/${id}`, { method: "POST" }),
    submitFeedback: (message_id, score) => apiFetch("/analytics/feedback", { method: "POST", body: { message_id, score } }),
    getDailyQuote: () => apiFetch("/gallery/daily_quote")
};

window.api = api;