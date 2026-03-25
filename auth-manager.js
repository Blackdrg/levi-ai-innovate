/**
 * LEVI Auth Manager v1.0
 * Handles auth state using httpOnly cookies (set by backend).
 * Stores only non-sensitive user display data in localStorage.
 * Import this on every page.
 */

'use strict';

// ─── API Base Detection ──────────────────────────────────────────────────────
const _isLocal =
  ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(location.hostname) ||
  location.hostname === '';

window.API_BASE = _isLocal
  ? `http://${location.hostname}:8000`
  : `${location.origin}/api`;

// ─── Fetch wrapper (always sends cookies) ───────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const url = `${window.API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    credentials: 'include',                          // always send cookies
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: options.body && typeof options.body !== 'string'
      ? JSON.stringify(options.body)
      : options.body,
  });

  if (res.status === 401) {
    // Token expired – clear stale UI data and redirect
    localStorage.removeItem('levi_user');
    if (!location.pathname.includes('auth.html')) {
      location.href = 'auth.html?expired=true';
    }
    throw new Error('Unauthorised');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}
window.apiFetch = apiFetch;

// ─── Auth helpers ────────────────────────────────────────────────────────────

/** Returns cached user object or null if not logged in. */
function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem('levi_user') || 'null');
  } catch { return null; }
}
window.getCurrentUser = getCurrentUser;

/** Fetches fresh user profile from API and caches it. */
async function refreshUserProfile() {
  try {
    const profile = await apiFetch('/users/me');
    localStorage.setItem('levi_user', JSON.stringify(profile));
    return profile;
  } catch {
    return null;
  }
}
window.refreshUserProfile = refreshUserProfile;

/** True if we have a cached user (optimistic check; 401 will correct it). */
function isLoggedIn() {
  return Boolean(getCurrentUser());
}
window.isLoggedIn = isLoggedIn;

/** Sign out: tell backend, clear cache, go home. */
async function logout() {
  try { await apiFetch('/logout', { method: 'POST' }); } catch { /* ignore */ }
  localStorage.removeItem('levi_user');
  location.href = 'index.html';
}
window.logout = logout;

// ─── Backend connectivity ────────────────────────────────────────────────────

let _backendOnline = false;
window.isBackendOnline = () => _backendOnline;

async function pingBackend() {
  try {
    const data = await apiFetch('/health');
    _backendOnline = data?.status === 'ok';
  } catch {
    _backendOnline = false;
  }

  // Update every status indicator on the page
  document.querySelectorAll('[data-status-dot]').forEach(el => {
    el.className = el.className.replace(/bg-\w+-\d+/, _backendOnline ? 'bg-emerald-400' : 'bg-red-500');
  });
  const label = document.getElementById('status-label');
  if (label) label.textContent = _backendOnline ? 'Live' : 'Offline';

  // Offline banner
  const banner = document.getElementById('offline-banner');
  if (banner) banner.style.display = _backendOnline ? 'none' : 'block';

  return _backendOnline;
}
window.pingBackend = pingBackend;

// ─── Nav UI ──────────────────────────────────────────────────────────────────

function updateNavUI() {
  const user = getCurrentUser();
  const btn  = document.getElementById('nav-auth-btn');
  if (!btn) return;

  if (user) {
    btn.textContent  = user.username || 'Account';
    btn.href         = 'my-gallery.html';
    btn.onclick      = null;
    // Update sidebar items
    document.querySelectorAll('[data-user-name]').forEach(el => { el.textContent = user.username; });
    document.querySelectorAll('[data-credits]').forEach(el => { el.textContent = `${user.credits ?? 0} credits`; });
  } else {
    btn.textContent = 'Sign In';
    btn.href        = 'auth.html';
  }
}
window.updateNavUI = updateNavUI;

// ─── Auto-init on every page ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Wake up backend (no-op if already up)
  pingBackend();
  setInterval(pingBackend, 30_000);

  // 2. Update nav
  updateNavUI();

  // 3. If logged in refresh profile silently (updates credits etc.)
  if (isLoggedIn()) {
    refreshUserProfile().then(updateNavUI);
  }
});
