// Common UI utilities for LEVI - Dark mode, favorites, copy, mood

import { trackShare, getHealth } from './api.js';

let favorites = JSON.parse(localStorage.getItem('levi_favorites')) || [];
let token = window.levi_user_token || null;
let currentMoods = [];

document.addEventListener('DOMContentLoaded', () => {
  // Init Connectivity Check
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

  // Global Error Boundary (Deep Debugging)
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason || {};
    const ridText = error.requestId ? ` (Ref: ${error.requestId.slice(0, 8)})` : "";
    
    console.error('Unhandled promise rejection:', error);
    showToast(`Cosmic interference detected${ridText}. Please try again.`, "error");
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
  const overlay = document.getElementById('offline-overlay');

  try {
    const data = await getHealth();
    const isHealthy = data && (data.status === 'ok' || data.status === 'healthy');

    if (overlay) {
      if (!isHealthy) {
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
      } else {
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
      }
    }
  } catch (err) {
    if (overlay) {
      overlay.classList.remove('hidden');
      overlay.classList.add('flex');
    }
  }
}

function showLoader() {
  const l = document.getElementById('global-loader');
  if (l) { l.style.width = '30%'; l.style.opacity = '1'; }
}

function hideLoader() {
  const l = document.getElementById('global-loader');
  if (l) { 
    l.style.width = '100%'; 
    setTimeout(() => { l.style.opacity = '0'; setTimeout(() => l.style.width = '0', 300); }, 200);
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

