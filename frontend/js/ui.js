// Common UI utilities for LEVI - Dark mode, favorites, copy, mood

import { trackShare, getHealth } from './api.js';

let favorites = JSON.parse(localStorage.getItem('levi_favorites')) || [];
let token = window.levi_user_token || null;
let currentMoods = [];

document.addEventListener('DOMContentLoaded', async () => {
  // Init Connectivity Check
  checkSystemStatus();
  setInterval(checkSystemStatus, 30000);

  // Sync User if already logged in (Local Storage persistence)
  if (window.syncUser) {
      setTimeout(() => window.syncUser(), 500); // Small delay to allow auth-manager to settle 
  }

  // Init dark mode
  if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
  }

  // Dark toggle listeners
  document.querySelectorAll('#dark-toggle').forEach(btn => {
    btn.addEventListener('click', toggleDarkMode);
  });

  // Global Error Boundary
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason || {};
    const msg = error.message || "Cosmic interference detected.";
    if (msg === "ALLOWANCE_EXCEEDED") {
        showToast("Daily allowance reached. Upgrade for more.", "warning");
    } else {
        showToast(msg, "error");
    }
  });

  // Initialize UI State
  if (window.updateUIState) {
    const u = localStorage.getItem('levi_user');
    if (u) {
        try { window.updateUIState(JSON.parse(u)); } catch(e) {}
    }
  }
});

function showToast(message, type = "info") {
  const existing = document.querySelector('.levi-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `levi-toast fixed bottom-10 left-1/2 -translate-x-1/2 px-6 py-3 rounded-full glass border border-white/10 text-[11px] uppercase tracking-widest font-bold z-[100] animate-fade-up shadow-[0_10px_40px_rgba(0,0,0,0.5)]`;
  
  let color = 'text-primary';
  if (type === 'error') color = 'text-red-400';
  if (type === 'warning') color = 'text-yellow-400';
  if (type === 'success') color = 'text-emerald-400';
  
  toast.classList.add(color);
  toast.innerText = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

async function checkSystemStatus() {
  const overlay = document.getElementById('offline-overlay');
  const dot = document.getElementById('status-dot');
  const label = document.getElementById('status-label');

  try {
    const data = await window.api.apiFetch("/health").catch(() => null);
    const isHealthy = data && (data.status === 'ok' || data.status === 'healthy');

    if (dot && label) {
        dot.className = `w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-amber-400'}`;
        label.textContent = isHealthy ? 'System Online' : 'Limited Service';
    }

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
    // Ignore transient errors to prevent flickering
  }
}

// Global Loader Overrides
window.showLoader = () => {
    const l = document.getElementById('global-loader');
    if (l) { l.style.width = '40%'; l.style.opacity = '1'; }
};
window.hideLoader = () => {
    const l = document.getElementById('global-loader');
    if (l) { 
        l.style.width = '100%'; 
        setTimeout(() => { l.style.opacity = '0'; setTimeout(() => l.style.width = '0', 300); }, 200);
    }
};

window.ui = {
  toggleDarkMode,
  copyToClipboard,
  showToast,
  showError: (msg) => showToast(msg, "error"),
  showSuccess: (msg) => showToast(msg, "success"),
  showWarning: (msg) => showToast(msg, "warning"),
  checkSystemStatus,
  showLoader: window.showLoader,
  hideLoader: window.hideLoader
};

