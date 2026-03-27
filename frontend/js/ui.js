// Common UI utilities for LEVI - Dark mode, favorites, copy, mood

import { trackShare, getHealth } from './api.js';

let favorites = JSON.parse(localStorage.getItem('levi_favorites')) || [];
let token = window.levi_user_token || null;
let currentMoods = [];

document.addEventListener('DOMContentLoaded', () => {
  // Init offline banner
  injectOfflineBanner();
  checkSystemStatus();
  setInterval(checkSystemStatus, 30000);

  // Init dark mode
  if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
  }

  // Init animations
  document.querySelectorAll('.animate-pulse-glow').forEach(el => {
    el.classList.add('animate-pulse-glow');
  });

  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
  });

  // Dark toggle listeners
  document.querySelectorAll('#dark-toggle').forEach(btn => {
    btn.addEventListener('click', toggleDarkMode);
  });

  // Global Error Boundary
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast("Cosmic interference detected. Please try again.", "error");
  });
});

function toggleDarkMode() {
  document.documentElement.classList.toggle('dark');
  localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
  document.querySelectorAll('#dark-toggle').forEach(btn => {
    btn.textContent = document.documentElement.classList.contains('dark') ? '☀️' : '🌙';
  });
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    // Visual feedback
    const btn = event.target;
    const original = btn.innerHTML;
    btn.innerHTML = '✅';
    btn.classList.add('animate-pulse');
    setTimeout(() => {
      btn.innerHTML = original;
      btn.classList.remove('animate-pulse');
    }, 1000);
  });
}

function toggleFavorite(quote) {
  const index = favorites.findIndex(f => f.quote === quote);
  if (index > -1) {
    favorites.splice(index, 1);
  } else {
    favorites.push({quote, author: quote.author || 'Anonymous'});
  }
  localStorage.setItem('levi_favorites', JSON.stringify(favorites));
}

function getAuthHeaders() {
  const t = window.levi_user_token || null;
  return t ? { 'Authorization': `Bearer ${t}` } : {};
}

let typingMessages = [];

function addTypingMessage() {
  const messages = document.getElementById('messages');
  if (!messages) return null;
  const typingId = 'typing_' + Date.now();
  const typingMsg = document.createElement('div');
  typingMsg.id = typingId;
  typingMsg.className = 'bot-msg typing-indicator p-4 rounded-2xl mr-auto max-w-xs lg:max-w-md bg-slate-800/80';
  typingMsg.innerHTML = `<div>LEVI is typing<span class="typing-dots ml-2"></span></div>`;
  messages.appendChild(typingMsg);
  messages.scrollTop = messages.scrollHeight;
  typingMessages.push(typingId);
  return typingId;
}

function removeTypingMessage(typingId) {
  const el = document.getElementById(typingId);
  if (el) el.remove();
  typingMessages = typingMessages.filter(id => id !== typingId);
}

// ── Web Push Notifications ──

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function subscribeToPush(vapidPublicKey) {
  try {
    const reg = await navigator.serviceWorker.ready;
    
    // Check for existing subscription
    let sub = await reg.pushManager.getSubscription();
    
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      });
    }

    await window.waitForToken();
    const token = window.levi_user_token;
    const res = await fetch(`${window.API_BASE}/push/subscribe`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(sub.toJSON())
    });

    if (res.ok) {
      showToast("Notifications enabled! ✨");
      return true;
    } else {
      throw new Error("Failed to save subscription on server");
    }
  } catch (err) {
    console.error("Push subscription error:", err);
    showToast("Failed to enable notifications.", "error");
    return false;
  }
}

function selectMood(mood, targetBtn) {
  const btn = targetBtn || (event && event.target);
  if (!btn) return;
  if (currentMoods.includes(mood)) {
    currentMoods = currentMoods.filter(m => m !== mood);
    btn.classList.remove('ring-4', 'ring-white/50');
  } else {
    currentMoods.push(mood);
    btn.classList.add('ring-4', 'ring-white/50');
  }
}

async function shareContent(title, text, url) {
  const shareData = { title, text, url };
  await window.waitForToken();
  const token = window.levi_user_token;

  try {
    if (navigator.share) {
      await navigator.share(shareData);
      window.ui.showToast("Shared successfully!");
    } else {
      copyToClipboard(url || text);
      window.ui.showToast("Link copied to clipboard!");
    }

    if (token) {
      const reward = await trackShare(token);
      if (reward && reward.rewarded) {
        window.ui.showToast("Bonus credits unlocked! 🎁 +10 Credits", "success");
      }
    }
  } catch (err) {
    console.error("Share failed:", err);
  }
}

function showToast(message, type = "info") {
  const toast = document.createElement('div');
  toast.className = `fixed bottom-10 left-1/2 -translate-x-1/2 px-6 py-3 rounded-full glass border border-white/10 text-sm font-medium z-[100] animate-fade-up ${type === 'error' ? 'text-red-400' : 'text-yellow-400'}`;
  toast.innerText = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

function injectOfflineBanner() {
  if (document.getElementById('offline-banner')) return;

  // Inject CSS
  if (!document.getElementById('offline-banner-style')) {
    const style = document.createElement('style');
    style.id = 'offline-banner-style';
    style.innerHTML = `
      .backend-offline {
        display: none;
        background: #ef4444;
        color: white;
        text-align: center;
        padding: 8px;
        font-size: 12px;
        font-weight: bold;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        position: fixed;
        top: 80px;
        left: 0;
        width: 100%;
        z-index: 1000;
      }
    `;
    document.head.appendChild(style);
  }

  const banner = document.createElement('div');
  banner.id = 'offline-banner';
  banner.className = 'backend-offline';
  banner.innerText = 'System Offline — Connecting to Cosmic Archive...';
  document.body.prepend(banner);
}

async function checkSystemStatus() {
  const statusIndicator = document.getElementById('status-indicator');
  const offlineBanner = document.getElementById('offline-banner');

  try {
    const data = await getHealth();
    const isHealthy = data && (data.status === 'ok' || data.status === 'healthy');

    if (statusIndicator) {
      statusIndicator.classList.toggle('bg-red-500', !isHealthy);
      statusIndicator.classList.toggle('bg-emerald-500', isHealthy);
      statusIndicator.title = isHealthy ? "System Online" : "System Offline";
    }

    if (offlineBanner) {
      offlineBanner.style.display = isHealthy ? 'none' : 'block';
    }
  } catch (err) {
    if (statusIndicator) {
      statusIndicator.classList.add('bg-red-500');
      statusIndicator.classList.remove('bg-emerald-500');
    }
    if (offlineBanner) {
      offlineBanner.style.display = 'block';
    }
  }
}

function injectLoader() {
  if (document.getElementById('global-loader')) return;
  const style = document.createElement('style');
  style.id = 'loader-style';
  style.innerHTML = `
    #global-loader {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(14, 14, 18, 0.75);
      backdrop-filter: blur(12px);
      z-index: 10000;
      align-items: center;
      justify-content: center;
      transition: opacity 0.3s;
    }
    .leviloader-spinner {
      width: 48px;
      height: 48px;
      border: 3px solid rgba(242, 202, 80, 0.1);
      border-top-color: #f2ca50;
      border-radius: 50%;
      animation: spin-loader 0.8s linear infinite;
      box-shadow: 0 0 20px rgba(242, 202, 80, 0.15);
    }
    @keyframes spin-loader { to { transform: rotate(360deg); } }
  `;
  document.head.appendChild(style);

  const loader = document.createElement('div');
  loader.id = 'global-loader';
  loader.innerHTML = '<div class="leviloader-spinner"></div>';
  document.body.appendChild(loader);
}

function showLoader() {
  injectLoader();
  const l = document.getElementById('global-loader');
  if (l) {
    l.style.display = 'flex';
    l.style.opacity = '1';
  }
}

function hideLoader() {
  const l = document.getElementById('global-loader');
  if (l) {
    l.style.opacity = '0';
    setTimeout(() => { l.style.display = 'none'; }, 300);
  }
}

// Attach to window for module access
window.ui = {
  toggleDarkMode,
  copyToClipboard,
  toggleFavorite,
  getAuthHeaders,
  addTypingMessage,
  removeTypingMessage,
  selectMood,
  shareContent,
  showToast,
  showError: (msg) => showToast(msg, "error"),
  injectOfflineBanner,
  checkSystemStatus,
  showLoader,
  hideLoader,
  currentMoods
};

