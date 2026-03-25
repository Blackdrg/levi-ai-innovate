/**
 * LEVI Chat v2.0
 * Uses cookie-based auth (no manual Bearer tokens).
 * Requires auth-manager.js loaded before this file.
 */

let currentMood  = 'philosophical';
let messageCount = 0;
let chatHistory  = [];
let lastBotMsg   = '';

// ── Helpers ──────────────────────────────────────────────────────────────────

function getSessionId() {
  let id = sessionStorage.getItem('levi_chat_session');
  if (!id) {
    id = 'session_' + Math.random().toString(36).slice(2);
    sessionStorage.setItem('levi_chat_session', id);
  }
  return id;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.innerHTML = `<div style="background:rgba(19,19,23,.92);border:.5px solid rgba(242,202,80,.35);
    backdrop-filter:blur(20px);border-radius:9999px;padding:10px 20px;
    box-shadow:0 8px 32px rgba(0,0,0,.5)">
    <span style="font-size:12px;color:#e5e1e7;font-weight:600;letter-spacing:.04em">${msg}</span>
  </div>`;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Mood ─────────────────────────────────────────────────────────────────────

function setMood(el, mood) {
  document.querySelectorAll('.mood-chip').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentMood = mood;
  const si = document.getElementById('session-info');
  if (si) si.textContent = `Anonymous · ${mood.charAt(0).toUpperCase() + mood.slice(1)} mode`;
}

// ── Input ────────────────────────────────────────────────────────────────────

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = `${el.scrollHeight}px`;
}

// ── Messages ─────────────────────────────────────────────────────────────────

function appendMessage(role, html, msgId = null) {
  const container = document.getElementById('messages');
  if (!container) return null;

  const wrap = document.createElement('div');
  wrap.className = `message-wrap flex ${role === 'user' ? 'justify-end' : 'justify-start'}`;

  const bubble = document.createElement('div');
  bubble.className = role === 'user' ? 'msg-user p-4 text-sm text-on-surface animate-in'
                                      : 'msg-bot p-4 text-sm text-on-surface-variant animate-in';

  // Render markdown if available
  let rendered = html;
  if (typeof marked !== 'undefined') {
    try { rendered = marked.parse(html); } catch { /* use raw */ }
  }
  bubble.innerHTML = rendered;

  if (role === 'bot') {
    // Feedback buttons
    const fbId = msgId || `msg_${Date.now()}`;
    const fbRow = document.createElement('div');
    fbRow.className = 'flex items-center gap-2 mt-2 pt-2 border-t border-white/10';
    fbRow.innerHTML = `
      <button onclick="submitFeedback('${fbId}', 5, this)"
        class="text-zinc-500 hover:text-emerald-400 transition-colors" title="Good">
        <span class="material-symbols-outlined" style="font-size:16px">thumb_up</span>
      </button>
      <button onclick="submitFeedback('${fbId}', 1, this)"
        class="text-zinc-500 hover:text-red-400 transition-colors" title="Poor">
        <span class="material-symbols-outlined" style="font-size:16px">thumb_down</span>
      </button>`;
    bubble.appendChild(fbRow);

    // Art suggestion every 3 messages
    if (messageCount > 0 && messageCount % 3 === 0) {
      const enc = encodeURIComponent(html.slice(0, 200));
      const art = document.createElement('div');
      art.className = 'mt-3 rounded-xl p-3 border border-primary/20 text-center';
      art.style.background = 'rgba(242,202,80,.06)';
      art.innerHTML = `<p class="text-xs text-on-surface mb-2">Turn this into visual art?</p>
        <a href="studio.html?quote=${enc}&mood=${currentMood}"
           class="btn-gold inline-block text-[10px] uppercase font-bold px-4 py-1.5 rounded-full">
          Create Art
        </a>`;
      bubble.appendChild(art);
    }

    lastBotMsg = html;
  }

  wrap.appendChild(bubble);
  container.appendChild(wrap);
  container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  return wrap;
}

// ── Send ─────────────────────────────────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text  = input?.value.trim();
  if (!text) return;

  appendMessage('user', text);
  input.value = '';
  if (input) input.style.height = 'auto';
  chatHistory.push({ user: text });

  // Loading state
  const sendIcon = document.getElementById('send-icon');
  const spinner  = document.getElementById('send-loading');
  if (sendIcon) sendIcon.classList.add('hidden');
  if (spinner)  spinner.classList.remove('hidden');

  try {
    const API = window.API_BASE || 'http://localhost:8000';
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      credentials: 'include',                  // ← cookies, no manual token
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: getSessionId(),
        message:    text,
        mood:       currentMood,
        lang:       localStorage.getItem('levi_lang') || 'en',
      }),
    });

    if (res.status === 429) {
      appendMessage('bot', 'Rate limit reached. Please wait a moment before sending another message.');
      return;
    }
    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const data = await res.json();
    messageCount++;

    const reply = data.response || data.reply || '…';
    appendMessage('bot', reply, data.id);
    chatHistory[chatHistory.length - 1].bot = reply;

  } catch (err) {
    appendMessage('bot', 'Could not reach the LEVI server. Make sure the backend is running.');
    console.error('[Chat]', err);
  } finally {
    if (sendIcon) sendIcon.classList.remove('hidden');
    if (spinner)  spinner.classList.add('hidden');
  }
}

// ── Feedback ─────────────────────────────────────────────────────────────────

async function submitFeedback(msgId, rating, btn) {
  const parent = btn?.parentElement;
  if (parent) parent.innerHTML =
    `<span class="text-[10px] text-emerald-400 uppercase tracking-widest">
       <span class="material-symbols-outlined align-middle" style="font-size:14px">check</span>
       Saved
     </span>`;

  try {
    await fetch(`${window.API_BASE}/feedback`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_id:   msgId,
        rating,
        session_id:   getSessionId(),
        message_hash: msgId,
        bot_response: lastBotMsg,
        user_message: chatHistory.length
          ? (chatHistory[chatHistory.length - 1].user || '')
          : '',
      }),
    });
  } catch { /* silently ignore */ }
}

// ── TTS ───────────────────────────────────────────────────────────────────────

function speakLast() {
  if (!lastBotMsg) { showToast('Nothing to speak yet.'); return; }
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }

  const utt = new SpeechSynthesisUtterance(lastBotMsg.replace(/[*#<>]/g, ''));
  const preferred = ['Google UK English Male', 'Daniel', 'Alex', 'Samantha'];
  const voices = speechSynthesis.getVoices();
  for (const name of preferred) {
    const v = voices.find(v => v.name.includes(name));
    if (v) { utt.voice = v; break; }
  }
  utt.rate = 0.9; utt.pitch = 0.95;
  speechSynthesis.speak(utt);
}

// ── Voice input ───────────────────────────────────────────────────────────────

let recognition;
function startVoice() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) { showToast('Voice input not supported in this browser.'); return; }

  if (!recognition) {
    recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = e => {
      let final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
      }
      if (final) {
        const inp = document.getElementById('chat-input');
        if (inp) { inp.value += (inp.value ? ' ' : '') + final; autoResize(inp); }
      }
    };
  }
  try { recognition.start(); } catch { recognition.stop(); }
}

// ── Clear ─────────────────────────────────────────────────────────────────────

function clearChat() {
  const el = document.getElementById('messages');
  if (el) el.innerHTML = `
    <div class="msg-bot p-4">
      <p class="text-sm text-on-surface-variant font-light">Chat cleared. What shall we explore?</p>
    </div>`;
  chatHistory  = [];
  messageCount = 0;
  lastBotMsg   = '';
}

// ── Toggle mobile menu ────────────────────────────────────────────────────────
function toggleMobileMenu() {
  const m = document.getElementById('mobile-menu');
  if (m) m.classList.toggle('hidden');
}

// ── Expose globals ────────────────────────────────────────────────────────────
window.setMood         = setMood;
window.handleKey       = handleKey;
window.autoResize      = autoResize;
window.sendMessage     = sendMessage;
window.clearChat       = clearChat;
window.speakLast       = speakLast;
window.startVoice      = startVoice;
window.submitFeedback  = submitFeedback;
window.toggleMobileMenu = toggleMobileMenu;

// ── Load marked.js if not present ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (typeof marked === 'undefined') {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    document.head.appendChild(s);
  }
});
