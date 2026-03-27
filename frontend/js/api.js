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
      if (res.status === 401) {
        console.warn("[LEVI] Unauthorized - redirecting to auth");
        if (!window.location.pathname.includes('auth.html')) {
          window.location.href = 'auth.html?expired=true';
        }
      }
      
      if (res.status === 402) {
        console.warn("[LEVI] Payment Required - opening pricing");
        if (window.ui && window.ui.showToast) {
          window.ui.showToast("Credits exhausted. Upgrade to continue.", "warning");
        }
        setTimeout(() => {
          window.location.href = 'pricing.html?exhausted=true';
        }, 2000);
      }

      const errorData = await res.json().catch(() => ({}));
      const errorMessage = errorData.error || errorData.detail || `API error: ${res.status}`;
      throw new Error(errorMessage);
    }
    return await res.json();
  } catch (error) {
    clearTimeout(id);
    console.error(`[LEVI] Fetch error for ${url}:`, error);
    
    const errorMsg = error.name === 'AbortError' || error.message === 'Timeout' 
      ? "Request timed out. Please try again." 
      : (error.message || "Network error");
      
    if (typeof showToast === 'function') {
      showToast(errorMsg, "error");
    } else if (window.ui && window.ui.showToast) {
      window.ui.showToast(errorMsg, "error");
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

export async function generateImage(topic, author = "LEVI AI", mood = "", custom_bg = null) {
  return apiFetch("/generate_image", {
    method: "POST",
    body: { text: topic, author, mood, custom_bg }
  });
}

export async function generateVideo(topic, mood = "", author = "LEVI Muse") {
  const options = {
    method: "POST",
    body: { text: topic, mood, author },
    credentials: 'include'
  };
  
  const url = `${API_BASE}/generate_video`;
  const res = await fetch(url, {
    ...options,
    body: JSON.stringify(options.body),
    headers: { "Content-Type": "application/json" }
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Video API error: ${res.status}`);
  }
  
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return await res.json();
  }
  
  return await res.blob();
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
    author: data.author || "LEVI AI",
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