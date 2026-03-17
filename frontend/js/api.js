// Detect environment and set base URL
if (window.location.protocol === 'file:') {
  console.error('[LEVI] Website cannot run via file:// protocol. Please use a local server.');
  alert('LEVI Error: You cannot open index.html directly by double-clicking it. \n\nPlease run "python run_app.py" in your terminal and visit http://localhost:8080');
}

// Fixed API_BASE logic to be more flexible (localhost, 127.0.0.1, 0.0.0.0, or any local IP)
// If we are running on a local development port (8080), the backend is on 8000.
let hostname = window.location.hostname;
if (hostname === '0.0.0.0') hostname = '127.0.0.1'; // Fix for Windows 0.0.0.0 destination issue

const isLocalDev = window.location.port === '8080' || 
                   hostname === 'localhost' || 
                   hostname === '127.0.0.1';

const API_BASE = isLocalDev
  ? `${window.location.protocol}//${hostname}:8000`
  : window.location.origin + '/api';

console.log(`[LEVI] API Base set to: ${API_BASE}`);

// For production deployment, ensure Nginx proxies /api/ to the backend service.
// On localhost, it connects directly to the uvicorn server at port 8000.

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const defaultOptions = {
    headers: {
      "Content-Type": "application/json"
    }
  };

  const finalOptions = { ...defaultOptions, ...options };
  if (options.body && typeof options.body !== 'string') {
    finalOptions.body = JSON.stringify(options.body);
  }

  try {
    const res = await fetch(url, finalOptions);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `API error: ${res.status}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`Fetch error for ${endpoint}:`, error);
    throw error;
  }
}

export async function chat(message, session = "user1") {
  const lang = localStorage.getItem('levi_lang') || 'en';
  return apiFetch("/chat", {
    method: "POST",
    body: { session_id: session, message, lang }
  });
}

// Auth Endpoints
export async function login(username, password) {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  const res = await fetch(`${API_BASE}/token`, {
    method: "POST",
    body: formData
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Login failed: ${res.status}`);
  }
  return await res.json();
}

export async function register(username, password) {
  return apiFetch("/register", {
    method: "POST",
    body: { username, password }
  });
}

export async function getProfile(token) {
  return apiFetch("/users/me", {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });
}

export async function searchQuotes(text, filters = {}) {
  return apiFetch("/search_quotes", {
    method: "POST",
    body: { text, ...filters, top_k: 5 }
  });
}

export async function generateQuote(topic, mood = "") {
  return apiFetch("/generate", {
    method: "POST",
    body: { text: topic, mood }
  });
}

export async function getDailyQuote() {
  return apiFetch("/daily_quote");
}

export async function getAnalytics() {
  return apiFetch("/analytics");
}

export async function generateQuoteImage(text, author = "Unknown", mood = "neutral", options = {}) {
  return apiFetch("/generate_image", {
    method: "POST",
    body: { text, author, mood, ...options }
  });
}

export async function getFeed(limit = 20) {
  return apiFetch(`/feed?limit=${limit}`);
}

export async function getAnalytics() {
  return apiFetch("/analytics");
}

export async function likeItem(type, id) {
  return apiFetch(`/like/${type}/${id}`, { method: "POST" });
}

// Attach to window for non-module scripts
window.api = {
  chat,
  login,
  register,
  getProfile,
  searchQuotes,
  generateQuote,
  getDailyQuote,
  generateQuoteImage,
  getAnalytics,
  getFeed,
  likeItem
};


