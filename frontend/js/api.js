/**
 * LEVI-AI Centralized API Layer
 * Phase 6: Production Hardened
 */

(function() {
    const getBase = () => {
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        return isLocal ? 'http://127.0.0.1:8000/api/v8' : (window.LEVI_CONFIG?.getApiBase() || '/api/v8');
    };

    const API_BASE = getBase();

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
        },
        showToast: (msg, type = 'info') => {
            if (window.ui && window.ui.showToast) {
                window.ui.showToast(msg, type);
            } else {
                console.log(`[API ${type}] ${msg}`);
            }
        }
    };

    const generateUUID = () => {
        return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    };

    async function apiFetch(endpoint, options = {}) {
        ui.showLoader();
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
        
        const token = localStorage.getItem('fb_token') || localStorage.getItem('levi_token');
        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Trace-ID": generateUUID(),
            "X-Request-ID": generateUUID(),
            ...options.headers
        };

        if (token && token !== "local-token") {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const finalOptions = { ...options, headers };
        if (options.body && typeof options.body !== 'string' && !(options.body instanceof FormData)) {
            finalOptions.body = JSON.stringify(options.body);
        }

        try {
            const res = await fetch(url, finalOptions);
            
            // Handle specific status codes
            if (res.status === 401) {
                // Token expired or invalid
                localStorage.removeItem('levi_token');
                if (!window.location.pathname.includes('auth.html')) {
                    ui.showToast("Session expired. Please log in again.", "warning");
                    setTimeout(() => window.location.href = 'auth.html', 2000);
                }
                throw new Error("UNAUTHORIZED");
            }

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                const errorMessage = errorData.detail || errorData.error || `Error ${res.status}`;
                throw new Error(errorMessage);
            }

            return await res.json();
        } catch (error) {
            if (error.message !== "UNAUTHORIZED") {
                ui.showToast(error.message, "error");
            }
            throw error;
        } finally {
            ui.finishLoader();
        }
    }

    const api = {
        // --- Auth ---
        login: (email, password) => apiFetch("/auth/login", { method: "POST", body: { email, password } }),
        signup: (email, password, username) => apiFetch("/auth/signup", { method: "POST", body: { email, password, username } }),
        logout: () => apiFetch("/auth/logout", { method: "POST" }),
        getMe: () => apiFetch("/auth/me"),
        getCredits: () => apiFetch("/auth/credits"),

        // --- Chat & Memory ---
        chat: (message, sessionId, mood = "philosophical") => 
            apiFetch("/chat", { method: "POST", body: { message, session_id: sessionId, mood } }),
        
        getMemory: () => apiFetch("/memory"),
        saveMemory: (fact, category = "general") => 
            apiFetch("/memory/save", { method: "POST", body: { fact, category } }),
        clearMemory: () => apiFetch("/memory/facts/clear-all", { method: "DELETE" }),

        // --- Search (Phase 6 Hardening) ---
        search: (query, sessionId, mood = "philosophical") => 
            apiFetch("/search", { method: "POST", body: { query, session_id: sessionId, mood } }),

        // --- AI Studio ---
        generateImage: (text, author, mood) => 
            apiFetch("/studio/generate_image", { method: "POST", body: { text, author, mood } }),
        generateVideo: (text, author, mood) => 
            apiFetch("/studio/generate_video", { method: "POST", body: { text, author, mood } }),
        getTaskStatus: (taskId) => apiFetch(`/studio/task_status/${taskId}`),

        // --- System ---
        getStatus: () => apiFetch("/status/stats"),
        getFeatures: () => apiFetch("/features/status"),
        getFeed: (limit = 10, page = 1) => apiFetch(`/gallery?limit=${limit}&page=${page}`),
        getMyGallery: () => apiFetch("/gallery/my_gallery"),
        likeItem: (type, id) => apiFetch(`/gallery/like/${id}`, { method: "POST", body: { type } }),
        trackShare: () => apiFetch("/analytics/track_share", { method: "POST" }),
        getDailyQuote: () => apiFetch("/daily_quote"),

        // --- File Handling ---
        upload: (file) => {
            const formData = new FormData();
            formData.append('file', file);
            // LEVI v6: Consolidated upload endpoint
            return apiFetch("/upload", { 
                method: "POST", 
                body: formData,
                headers: {} // Let browser set boundary
            });
        },

        // --- Streaming (V8 Hardened) ---
        chatStream: async (message, sessionId, onChunk, onMetadata, mood = "philosophical", history = []) => {
            const url = `${API_BASE}/mission/stream`;
            const token = localStorage.getItem('levi_token') || window.levi_user_token;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'Accept': 'text/event-stream',
                    'Authorization': token ? `Bearer ${token}` : ''
                },
                body: JSON.stringify({ input: message, session_id: sessionId, context: { mood, history } })
            });

            if (!response.ok) throw new Error(`Mission stream failed: ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let partial = '';
            let currentEvent = 'message';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                partial += decoder.decode(value, { stream: true });
                const lines = partial.split('\n');
                partial = lines.pop();

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;

                    if (trimmed.startsWith('event: ')) {
                        currentEvent = trimmed.slice(7);
                    } else if (trimmed.startsWith('data: ')) {
                        const dataStr = trimmed.slice(6);
                        if (dataStr === '[DONE]') break;
                        
                        try {
                            const data = JSON.parse(dataStr);
                            // Standardize V8 Event Handling
                            if (currentEvent === 'token') {
                                onChunk(data.token || data);
                            } else {
                                onMetadata({ event: currentEvent, data: data });
                            }
                        } catch (e) {
                            // Fallback for non-JSON tokens if any
                            if (currentEvent === 'token') onChunk(dataStr);
                        }
                        // Reset event to default
                        currentEvent = 'message';
                    }
                }
            }
        }
    };

    window.api = api;
    window.API_BASE = API_BASE;
})();