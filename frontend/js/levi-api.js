// levi-api.js - Unified API client for LEVI-AI frontend
// Provides GET, POST, GET-SSE, POST-SSE with JWT auto-refresh on 401

class LeviAPI {
  constructor() {
    this.baseUrl = window.API_BASE || '';
    this.jwt = null;
    this.refreshInProgress = false;
    this.refreshQueue = [];
  }

  // Set JWT token (called after login)
  setToken(token) {
    this.jwt = token;
    localStorage.setItem('levi_jwt', token);
  }

  // Load token from storage if present
  loadToken() {
    const token = localStorage.getItem('levi_jwt');
    if (token) this.jwt = token;
  }

  // Internal fetch wrapper
  async _fetch(path, options = {}, retry = true) {
    const url = `${this.baseUrl}${path}`;
    const headers = options.headers || {};
    if (this.jwt) {
      headers['Authorization'] = `Bearer ${this.jwt}`;
    }
    const resp = await fetch(url, { ...options, headers });
    if (resp.status === 401 && retry) {
      // Attempt token refresh
      await this._refreshToken();
      return this._fetch(path, options, false);
    }
    return resp;
  }

  async _refreshToken() {
    if (this.refreshInProgress) {
      // Queue callers until refresh finishes
      return new Promise(resolve => this.refreshQueue.push(resolve));
    }
    this.refreshInProgress = true;
    try {
      const refreshResp = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshResp.ok) {
        const data = await refreshResp.json();
        this.setToken(data.access_token);
        this.refreshQueue.forEach(cb => cb());
        this.refreshQueue = [];
      } else {
        console.warn('[LeviAPI] Token refresh failed');
        this.jwt = null;
        localStorage.removeItem('levi_jwt');
        this.refreshQueue.forEach(cb => cb());
        this.refreshQueue = [];
      }
    } finally {
      this.refreshInProgress = false;
    }
  }

  async get(path) {
    const resp = await this._fetch(path, { method: 'GET' });
    return resp.json();
  }

  async post(path, body) {
    const resp = await this._fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return resp.json();
  }

  // GET SSE stream
  getStream(path, onMessage) {
    const url = `${this.baseUrl}${path}`;
    const eventSource = new EventSource(url, { withCredentials: true });
    eventSource.onmessage = e => onMessage(JSON.parse(e.data));
    eventSource.onerror = err => console.error('[LeviAPI] SSE error', err);
    return eventSource;
  }

  // POST SSE stream (multipart response)
  async postStream(path, body, onMessage) {
    const url = `${this.baseUrl}${path}`;
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    const processChunk = async () => {
      const { done, value } = await reader.read();
      if (done) return;
      const text = decoder.decode(value, { stream: true });
      // Assume each line is a JSON event
      text.split('\n').forEach(line => {
        if (line.trim()) {
          try { onMessage(JSON.parse(line)); } catch (_) {}
        }
      });
      await processChunk();
    };
    await processChunk();
  }
}

// Export a singleton for global use
window.LeviAPI = new LeviAPI();
window.LeviAPI.loadToken();
