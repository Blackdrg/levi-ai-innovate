// Common UI utilities for LEVI - Dark mode, favorites, copy, mood

let favorites = JSON.parse(localStorage.getItem('levi_favorites')) || [];
let token = localStorage.getItem('levi_token') || null;
let currentMoods = [];

document.addEventListener('DOMContentLoaded', () => {
  // Init light mode
  if (localStorage.getItem('lightMode') === 'true') {
    document.documentElement.classList.add('light');
  }

  // Update Nav based on Auth
  updateNav();

  // Offline handler
  window.addEventListener('offline', () => {
    showToast('You are offline. Some features may be limited.', 'error');
  });
  window.addEventListener('online', () => {
    showToast('Back online! Wisdom restored.', 'success');
  });

  // Language Init
  const savedLang = localStorage.getItem('levi_lang') || 'en';
  setLanguage(savedLang);

  // Audio Init
  initAmbientAudio();

  // Connection Check
  checkConnection();

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

async function checkConnection() {
  const statusEl = document.createElement('div');
  statusEl.id = 'connection-status';
  statusEl.className = 'fixed bottom-4 right-4 z-[9999] px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest glass transition-all opacity-0 pointer-events-none';
  document.body.appendChild(statusEl);

  try {
    const { getAnalytics } = await import('./api.js');
    await getAnalytics();
    statusEl.innerText = 'Connected to Core';
    statusEl.classList.add('text-emerald-400', 'opacity-50');
  } catch (err) {
    console.error('[LEVI] Connection test failed:', err);
    statusEl.innerText = 'Connection Issues Detected';
    statusEl.classList.add('text-red-400', 'opacity-100', 'animate-pulse');
    statusEl.classList.remove('pointer-events-none');
    statusEl.style.cursor = 'help';
    statusEl.title = 'The frontend cannot reach the backend. Ensure "python run_app.py" is running in your terminal.';
  }
}

function updateNav() {
  const user = localStorage.getItem('levi_user');
  const navContainer = document.querySelector('nav .flex.gap-4.items-center') || document.querySelector('nav div.flex');
  if (!navContainer) return;

  const dynamicClass = 'levi-dynamic-nav';
  navContainer.querySelectorAll(`.${dynamicClass}`).forEach(el => el.remove());

  let navHTML = '';
  if (user) {
    navHTML = `
      <div class="flex items-center gap-2 ${dynamicClass}">
        <span class="text-[10px] font-bold text-muted uppercase tracking-widest">${user}</span>
        <button onclick="logout()" class="text-[10px] text-red-400 hover:text-red-300 transition-colors">Logout</button>
      </div>
      <a href="my-gallery.html" class="glass px-3 py-2 rounded-xl text-xs hover:bg-white/5 transition-all ${dynamicClass}">Studio</a>
      <a href="feed.html" class="glass px-3 py-2 rounded-xl text-xs hover:bg-white/5 transition-all ${dynamicClass}">Feed</a>
    `;
  } else {
    navHTML = `
      <a href="auth.html" class="btn-primary px-4 py-2 rounded-xl text-xs ${dynamicClass}">Login</a>
    `;
  }
  
  navContainer.insertAdjacentHTML('beforeend', navHTML);
}

function logout() {
  localStorage.removeItem('levi_token');
  localStorage.removeItem('levi_user');
  window.location.href = 'index.html';
}

const translations = {
  en: {
    heroTitle: "LEVI AI",
    heroSub: "Experience the fusion of artificial intelligence and artistic inspiration. Wisdom, quotes, and visual art at your fingertips.",
    dailyTitle: "Daily Inspiration",
    startChat: "Start Conversation →",
    browseGallery: "Browse Gallery",
    feeling: "How are you feeling today?"
  },
  hi: {
    heroTitle: "लेवी AI",
    heroSub: "कृत्रिम बुद्धिमत्ता और कलात्मक प्रेरणा के मिलन का अनुभव करें। ज्ञान, विचार और कला आपकी उंगलियों पर।",
    dailyTitle: "आज का विचार",
    startChat: "बातचीत शुरू करें →",
    browseGallery: "गैलरी देखें",
    feeling: "आज आप कैसा महसूस कर रहे हैं?"
  }
};

function setLanguage(lang) {
  localStorage.setItem('levi_lang', lang);
  const t = translations[lang];
  if (!t) return;

  const mapping = {
    'h1': t.heroTitle,
    '.hero p': t.heroSub,
    '#daily-quote-card h3': t.dailyTitle,
    'a[href="chat.html"]': t.startChat,
    'a[href="quotes.html"].glass': t.browseGallery,
    '.mood-selector-title': t.feeling,
    'a[href="feed.html"]': "Feed"
  };

  for (const [selector, text] of Object.entries(mapping)) {
    const el = document.querySelector(selector);
    if (el) el.innerText = text;
  }
}

let ambientAudio = null;
function initAmbientAudio() {
    const nav = document.querySelector('nav div.flex');
    if (!nav) return;

    const audioBtn = document.createElement('button');
    audioBtn.id = 'ambient-toggle';
    audioBtn.className = 'glass p-2 rounded-xl hover:bg-white/5 transition-all ml-2';
    audioBtn.innerHTML = '🔇';
    audioBtn.title = "Ambient Soundscapes";
    nav.prepend(audioBtn);

    audioBtn.onclick = () => {
        if (!ambientAudio) {
            ambientAudio = new Audio('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3');
            ambientAudio.loop = true;
            ambientAudio.volume = 0.2;
        }

        if (ambientAudio.paused) {
            ambientAudio.play();
            audioBtn.innerHTML = '🔊';
            showToast('Ambient soundscape active...');
        } else {
            ambientAudio.pause();
            audioBtn.innerHTML = '🔇';
        }
    };
}

window.toggleLanguage = () => {
  const current = localStorage.getItem('levi_lang') || 'en';
  const next = current === 'en' ? 'hi' : 'en';
  setLanguage(next);
  showToast(`Language switched to ${next === 'en' ? 'English' : 'हिंदी'}`);
};

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `fixed bottom-8 left-1/2 -translate-x-1/2 glass px-8 py-4 rounded-2xl z-[100] animate-fade-in-up border ${type === 'error' ? 'border-red-500/50 text-red-400' : 'border-emerald-500/50 text-emerald-400'}`;
  toast.innerHTML = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function toggleDarkMode() {
  const isLight = document.documentElement.classList.toggle('light');
  localStorage.setItem('lightMode', isLight);
  document.querySelectorAll('#dark-toggle').forEach(btn => {
    btn.textContent = isLight ? '🌙' : '☀️';
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

async function likeQuote(btn, quoteText) {
  const user = localStorage.getItem('levi_user') || 'anonymous';
  const likes = JSON.parse(localStorage.getItem(`levi_likes_${user}`)) || [];
  
  const index = likes.indexOf(quoteText);
  if (index > -1) {
    likes.splice(index, 1);
    btn.innerHTML = btn.innerHTML.includes('Like') ? '🤍 Like' : '🤍';
    btn.classList.remove('text-pink-400');
  } else {
    likes.push(quoteText);
    btn.innerHTML = btn.innerHTML.includes('Like') ? '❤️ Liked' : '❤️';
    btn.classList.add('text-pink-400');
    
    // Call backend to sync global likes if we have an ID
    if (btn.dataset.id && btn.dataset.type) {
      try {
        const api = window.api || (await import('./api.js'));
        const res = await api.likeItem(btn.dataset.type, btn.dataset.id);
        if (btn.innerHTML.includes('❤️')) {
          btn.innerHTML = btn.dataset.type === 'feed' ? `❤️ ${res.new_likes}` : '❤️ Liked';
        }
      } catch (err) {
        console.error("Global like sync failed", err);
      }
    }
  }
  localStorage.setItem(`levi_likes_${user}`, JSON.stringify(likes));
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

async function regenerateChat(btn, oldText) {
  const container = btn.closest('.glass-card') || btn.closest('.message-bubble');
  const textEl = container ? (container.querySelector('.text-md') || container.querySelector('.text-2xl') || container.querySelector('p')) : null;
  if (!textEl) {
    console.error('Could not find text element for regeneration');
    return;
  }
  
  btn.classList.add('animate-spin');
  textEl.classList.add('opacity-50');
  
  try {
    const api = window.api || (await import('./api.js'));
    const response = await api.chat(`Regenerate wisdom similar to: ${oldText}`);
    textEl.innerText = response.response;
    // Update other buttons that depend on text
    const buttons = container.querySelectorAll('button');
    buttons.forEach(b => {
      const onclick = b.getAttribute('onclick');
      if (onclick && onclick.includes(oldText.replace(/'/g, "\\'"))) {
        b.setAttribute('onclick', onclick.replace(oldText.replace(/'/g, "\\'"), response.response.replace(/'/g, "\\'")));
      }
    });
  } catch (err) {
    console.error('Regeneration failed:', err);
    showToast('Failed to regenerate wisdom.', 'error');
  } finally {
    btn.classList.remove('animate-spin');
    textEl.classList.remove('opacity-50');
  }
}

window.likeQuote = likeQuote;
window.regenerateChat = regenerateChat;

// Attach to window for module access
window.ui = {
  toggleDarkMode,
  copyToClipboard,
  toggleFavorite,
  getAuthHeaders,
  addTypingMessage,
  removeTypingMessage,
  selectMood,
  likeQuote,
  currentMoods
};

