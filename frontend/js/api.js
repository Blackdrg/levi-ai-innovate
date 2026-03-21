// Detect environment and set base URL
if (window.location.protocol === 'file:') {
  console.error('[LEVI] Website cannot run via file:// protocol. Please use a local server.');
  alert('LEVI Error: You cannot open index.html directly. Run "python run_app.py" and visit http://localhost:8080');
}

const isLocalDev = (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.hostname === '0.0.0.0'
);

const API_BASE = isLocalDev
  ? `http://127.0.0.1:8000`
  : `${window.location.origin}/api`;

console.log(`[LEVI] API Base: ${API_BASE} | isLocalDev: ${isLocalDev}`);

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const defaultOptions = {
    headers: { "Content-Type": "application/json" }
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
    console.error(`[LEVI] Fetch error for ${url}:`, error);
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

export async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const res = await fetch(`${API_BASE}/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
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
    headers: { "Authorization": `Bearer ${token}` }
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

export async function generateImage(topic, author = "LEVI AI", mood = "", custom_bg = null, token = null) {
  const options = {
    method: "POST",
    body: { text: topic, author, mood, custom_bg }
  };
  if (token) {
    options.headers = { "Authorization": `Bearer ${token}` };
  }
  return apiFetch("/generate_image", options);
}

export async function generateVideo(topic, mood = "", author = "LEVI Muse", token = null) {
  const options = {
    method: "POST",
    body: { text: topic, mood, author }
  };
  if (token) {
    options.headers = { "Authorization": `Bearer ${token}` };
  }
  
  // Videos are returned as blobs
  const url = `${API_BASE}/generate_video`;
  const res = await fetch(url, {
    ...options,
    body: JSON.stringify(options.body),
    headers: { ...options.headers, "Content-Type": "application/json" }
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Video API error: ${res.status}`);
  }
  
  // Handle Celery response if enabled
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return await res.json();
  }
  
  return await res.blob();
}

export async function trackShare(token) {
  return apiFetch("/track_share", {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });
}

export async function getCredits(token) {
  return apiFetch("/credits", {
    headers: { "Authorization": `Bearer ${token}` }
  });
}

export async function createCheckout(plan, token) {
  return apiFetch(`/create_checkout?plan=${plan}`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });
}

export async function getDailyQuote() {
  const data = await apiFetch("/daily_quote");
  // Normalize response for consistency
  return {
    text: data.quote || data.text,
    author: data.author || "LEVI AI",
    topic: data.topic || "Philosophical"
  };
}

// ✅ Single definition — duplicate was causing module load failure
export async function getAnalytics() {
  return apiFetch("/analytics");
}

export async function generateQuoteImage(text, author = "Unknown", mood = "neutral", custom_bg = null, token = null) {
  return generateImage(text, author, mood, custom_bg, token);
}

export async function getFeed(limit = 20) {
  return apiFetch(`/feed?limit=${limit}`);
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
  generateImage,
  getAnalytics,
  getFeed,
  likeItem
};