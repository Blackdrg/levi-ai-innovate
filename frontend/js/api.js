const API_BASE = window.API_BASE;

console.log(`[LEVI] API Base: ${API_BASE}`);


async function getHealth() {
  return apiFetch("/health");
}


async function fetchWithRetry(url, options, retries = 2) {
  try {
    const res = await Promise.race([
      fetch(url, options),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error("Timeout")), 15000)
      )
    ]);
    
    if (!res.ok && retries > 0 && res.status >= 500) {
      console.warn(`[LEVI] Retrying ${url}... (${retries} left)`);
      return fetchWithRetry(url, options, retries - 1);
    }
    return res;
  } catch (err) {
    if (retries > 0) {
      console.warn(`[LEVI] Retrying ${url} after error: ${err.message}... (${retries} left)`);
      return fetchWithRetry(url, options, retries - 1);
    }
    throw err;
  }
}

async function apiFetch(endpoint, options = {}) {
  if (window.waitForToken) await window.waitForToken();
  const url = `${API_BASE}${endpoint}`;
  
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 15000);

  const defaultOptions = {
    headers: { "Content-Type": "application/json" },
    credentials: 'include',
    signal: controller.signal
  };

  const finalOptions = { ...defaultOptions, ...options };
  if (options.body && typeof options.body !== 'string') {
    finalOptions.body = JSON.stringify(options.body);
  }

  try {
    const res = await fetchWithRetry(url, finalOptions);
    clearTimeout(id);

    if (!res.ok) {
      // 1. Specific status handling
      if (res.status === 401) {
        console.warn("[LEVI] Unauthorized - redirecting to auth");
        if (!window.location.pathname.includes('auth.html')) {
          window.location.href = 'auth.html?expired=true';
        }
      }
      
      if (res.status === 402) {
        console.warn("[LEVI] Payment Required");
        if (window.ui && window.ui.showToast) {
          window.ui.showToast("Credits exhausted. Upgrade to continue.", "warning");
        }
        return; // Let caller handle or wait for redirect
      }

      // 2. Parse standardized error response
      let errorData = {};
      try {
        errorData = await res.json();
      } catch (e) {
        errorData = { error: `HTTP ${res.status}` };
      }

      const errorMessage = errorData.error || errorData.detail || `Server error (${res.status})`;
      const requestId = errorData.request_id || res.headers.get("X-Request-ID");
      
      console.error(`[LEVI] API Error: ${errorMessage}`, { 
        status: res.status, 
        requestId,
        url 
      });

      const finalError = new Error(errorMessage);
      finalError.requestId = requestId;
      finalError.status = res.status;
      throw finalError;
    }
    return await res.json();
  } catch (error) {
    clearTimeout(id);
    
    let displayMsg = error.message || "Network error";
    if (error.name === 'AbortError' || error.message === 'Timeout') {
        displayMsg = "Request timed out. Please check your connection.";
    }

    console.error(`[LEVI] Fetch failed:`, error);
    
    const toast = (window.ui && window.ui.showToast) || window.showToast;
    if (toast) {
      const ridText = error.requestId ? ` (Ref: ${error.requestId.slice(0, 8)})` : "";
      toast(`${displayMsg}${ridText}`, "error");
    }
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
  return apiFetch("/login", {
    method: "POST",
    body: { username, password }
  });
}

export async function register(username, password) {
  return apiFetch("/register", {
    method: "POST",
    body: { username, password }
  });
}

export async function getProfile() {
  return apiFetch("/users/me");
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

export async function generateImage(topic, author = "LEVI-AI", mood = "", custom_bg = null) {
  return apiFetch("/generate_image", {
    method: "POST",
    body: { text: topic, author, mood, custom_bg }
  });
}

export async function generateVideo(topic, mood = "", author = "LEVI Muse") {
  return apiFetch("/generate_video", {
    method: "POST",
    body: { text: topic, mood, author },
  });
}

export async function trackShare() {
  return apiFetch("/track_share", { method: "POST" });
}

export async function getCredits() {
  return apiFetch("/credits");
}

export async function createCheckout(plan) {
  return apiFetch(`/create_checkout?plan=${plan}`, { method: "POST" });
}

export async function getDailyQuote() {
  const data = await apiFetch("/daily_quote");
  return {
    text: data.quote || data.text,
    author: data.author || "LEVI-AI",
    topic: data.topic || "Philosophical"
  };
}

export async function getAnalytics() {
  return apiFetch("/analytics");
}

export async function generateQuoteImage(text, author = "Unknown", mood = "neutral", custom_bg = null) {
  return generateImage(text, author, mood, custom_bg);
}

export async function getFeed(limit = 20) {
  return apiFetch(`/feed?limit=${limit}`);
}

export async function likeItem(type, id) {
  return apiFetch(`/like/${type}/${id}`, { method: "POST" });
}

export async function getTaskStatus(taskId) {
  return apiFetch(`/task_status/${taskId}`);
}

export async function getMyGallery() {
  return apiFetch("/my_gallery");
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
  likeItem,
  getHealth,
  getTaskStatus,
  getMyGallery,
  trackShare,
  getCredits,
  createCheckout
};