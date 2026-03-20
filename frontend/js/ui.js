// Common UI utilities for LEVI - Dark mode, favorites, copy, mood

import { trackShare } from './api.js';

let favorites = JSON.parse(localStorage.getItem('levi_favorites')) || [];
let token = localStorage.getItem('levi_token') || null;
let currentMoods = [];

document.addEventListener('DOMContentLoaded', () => {
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
  return token ? { 'Authorization': `Bearer ${token}` } : {};
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
  const token = localStorage.getItem('levi_token');

  try {
    if (navigator.share) {
      await navigator.share(shareData);
      window.ui.showToast("Shared successfully!");
      if (token) await trackShare(token);
    } else {
      copyToClipboard(url || text);
      window.ui.showToast("Link copied to clipboard!");
      if (token) await trackShare(token);
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
  currentMoods
};

