/**
 * LEVI API Client v2.0
 * All requests use httpOnly cookies (credentials:'include').
 * No Bearer tokens are stored or sent manually.
 */

// API_BASE is set by auth-manager.js which must be loaded first.
// Fallback so this file works standalone too.
if (!window.API_BASE) {
  window.API_BASE = ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(location.hostname)
    ? `http://${location.hostname}:8000`
    : `${location.origin}/api`;
}

// ── Core fetch ───────────────────────────────────────────────────────────────
async function _fetch(endpoint, options = {}) {
  // Use the shared wrapper if available, otherwise build our own
  if (window.apiFetch) return window.apiFetch(endpoint, options);

  const url = `${window.API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: options.body && typeof options.body !== 'string'
      ? JSON.stringify(options.body)
      : options.body,
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Public API surface ───────────────────────────────────────────────────────

export async function getHealth() {
  return _fetch('/health');
}

export async function login(username, password) {
  // Backend sets httpOnly cookie on success
  return _fetch('/login', { method: 'POST', body: { username, password } });
}

export async function register(username, password, email) {
  return _fetch('/register', { method: 'POST', body: { username, password, email } });
}

export async function getProfile() {
  return _fetch('/users/me');
}

export async function chat(message, session_id = 'default', mood = '', lang = 'en') {
  return _fetch('/chat', { method: 'POST', body: { session_id, message, mood, lang } });
}

export async function searchQuotes(text, filters = {}) {
  return _fetch('/search_quotes', { method: 'POST', body: { text, top_k: 5, ...filters } });
}

export async function generateQuote(topic, mood = '') {
  return _fetch('/generate', { method: 'POST', body: { text: topic, mood } });
}

export async function generateImage(text, author = 'LEVI AI', mood = 'neutral', custom_bg = null) {
  return _fetch('/generate_image', { method: 'POST', body: { text, author, mood, custom_bg } });
}

export async function generateVideo(text, mood = 'neutral', author = 'LEVI Muse') {
  return _fetch('/generate_video', { method: 'POST', body: { text, mood, author } });
}

export async function generateContent(type, topic, tone = 'inspiring', depth = 'high') {
  return _fetch('/generate_content', { method: 'POST', body: { type, topic, tone, depth } });
}

export async function getDailyQuote() {
  const d = await _fetch('/daily_quote');
  return { text: d.quote || d.text, author: d.author || 'LEVI AI', topic: d.topic || 'Wisdom' };
}

export async function getAnalytics() {
  return _fetch('/analytics');
}

export async function getFeed(limit = 20) {
  return _fetch(`/feed?limit=${limit}`);
}

export async function likeItem(type, id) {
  return _fetch(`/like/${type}/${id}`, { method: 'POST' });
}

export async function getMyGallery(limit = 20) {
  return _fetch(`/my_gallery?limit=${limit}`);
}

export async function trackShare() {
  return _fetch('/track_share', { method: 'POST' });
}

export async function getCredits() {
  return _fetch('/credits');
}

export async function getTaskStatus(taskId) {
  return _fetch(`/task_status/${taskId}`);
}

export async function createOrder(plan) {
  return _fetch('/create_order', { method: 'POST', body: { plan } });
}

// Alias
export const generateQuoteImage = generateImage;

// ── Attach to window for non-module scripts ──────────────────────────────────
window.api = {
  getHealth, login, register, getProfile, chat,
  searchQuotes, generateQuote, generateImage, generateQuoteImage,
  generateVideo, generateContent, getDailyQuote, getAnalytics,
  getFeed, likeItem, getMyGallery, trackShare, getCredits,
  getTaskStatus, createOrder,
};
