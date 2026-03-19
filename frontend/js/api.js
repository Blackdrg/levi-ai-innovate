if (window.location.protocol === 'file:') {
  console.error('[LEVI] Website cannot run via file:// protocol. Please use a local server.');
  alert('LEVI Error: Run "python run_app.py" and visit http://localhost:8080');
}

let hostname = window.location.hostname;
if (hostname === '0.0.0.0') hostname = '127.0.0.1';

const isLocalDev = window.location.port === '8080' || hostname === 'localhost' || hostname === '127.0.0.1';
export const API_BASE = isLocalDev
  ? `${window.location.protocol}//${hostname}:8000`
  : window.location.origin + '/api';

console.log(`[LEVI] API Base: ${API_BASE}`);

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const finalOptions = { headers: { 'Content-Type': 'application/json' }, ...options };
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
    console.error(`[LEVI] Fetch error for ${endpoint}:`, error);
    throw error;
  }
}

export async function chat(message, session = 'user1') {
  const lang = localStorage.getItem('levi_lang') || 'en';
  return apiFetch('/chat', { method: 'POST', body: { session_id: session, message, lang } });
}
export async function login(username, password) {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  const res = await fetch(`${API_BASE}/token`, { method: 'POST', body: formData });
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Login failed: ${res.status}`); }
  return res.json();
}
export async function register(username, password) {
  return apiFetch('/register', { method: 'POST', body: { username, password } });
}
export async function getProfile(token) {
  return apiFetch('/users/me', { headers: { Authorization: `Bearer ${token}` } });
}
export async function searchQuotes(text, filters = {}) {
  return apiFetch('/search_quotes', { method: 'POST', body: { text, ...filters, top_k: 5 } });
}
export async function generateQuote(topic, mood = '') {
  return apiFetch('/generate', { method: 'POST', body: { text: topic, mood } });
}
export async function getDailyQuote() { return apiFetch('/daily_quote'); }
export async function getAnalytics() { return apiFetch('/analytics'); }
export async function generateQuoteImage(text, author = 'Unknown', mood = 'neutral', options = {}) {
  return apiFetch('/generate_image', { method: 'POST', body: { text, author, mood, ...options } });
}
export async function getFeed(limit = 20) { return apiFetch(`/feed?limit=${limit}`); }
export async function likeItem(type, id) { return apiFetch(`/like/${type}/${id}`, { method: 'POST' }); }

window.api = { chat, login, register, getProfile, searchQuotes, generateQuote, getDailyQuote, generateQuoteImage, getAnalytics, getFeed, likeItem };
