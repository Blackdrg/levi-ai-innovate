/**
 * LEVI Feedback Widget
 * Attaches a star-rating panel to every bot message.
 * Submits ratings to POST /feedback which feeds the learning system.
 * Drop-in: <script src="js/feedback.js" type="module"></script>
 */

'use strict';

const API_BASE = window.API_BASE;

// ─────────────────────────────────────────────
// Feedback panel factory
// ─────────────────────────────────────────────
function createFeedbackPanel(userMessage, botResponse, mood, sessionId) {
  const panel = document.createElement('div');
  panel.className = 'levi-feedback-panel';
  panel.innerHTML = `
    <div class="lf-label">Rate this response</div>
    <div class="lf-stars" role="group" aria-label="Rate 1 to 5 stars">
      ${[1,2,3,4,5].map(n => `
        <button class="lf-star" data-val="${n}" aria-label="${n} star${n>1?'s':''}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
        </button>
      `).join('')}
    </div>
    <div class="lf-thanks" aria-live="polite"></div>
  `;

  const stars = panel.querySelectorAll('.lf-star');
  const thanks = panel.querySelector('.lf-thanks');
  let submitted = false;

  // Hover highlight
  stars.forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      if (submitted) return;
      const val = parseInt(btn.dataset.val);
      stars.forEach(s => s.classList.toggle('lf-hover', parseInt(s.dataset.val) <= val));
    });
  });
  panel.querySelector('.lf-stars').addEventListener('mouseleave', () => {
    stars.forEach(s => s.classList.remove('lf-hover'));
  });

  // Click to submit
  stars.forEach(btn => {
    btn.addEventListener('click', async () => {
      if (submitted) return;
      submitted = true;
      const rating = parseInt(btn.dataset.val);

      // Immediate visual feedback
      stars.forEach(s => {
        const val = parseInt(s.dataset.val);
        s.classList.toggle('lf-selected', val <= rating);
        s.classList.remove('lf-hover');
        s.disabled = true;
      });

      thanks.textContent = rating >= 4 ? '✦ Thank you!' : 'Thanks — I\'ll improve.';
      thanks.classList.add('lf-thanks-show');

      // Submit to backend
      try {
        await window.waitForToken();
        const token = localStorage.getItem('levi_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;

        await fetch(`${API_BASE}/feedback`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            session_id:    sessionId,
            message_hash:  await _hash(userMessage),
            rating:        rating,
            bot_response:  botResponse,
            user_message:  userMessage,
            mood:          mood || 'philosophical',
            feedback_type: 'star',
          }),
        });
      } catch (e) {
        console.warn('[LEVI Feedback] Submit failed:', e);
      }

      // Collapse panel after 2.5s
      setTimeout(() => {
        panel.classList.add('lf-collapsed');
        setTimeout(() => panel.remove(), 400);
      }, 2500);
    });
  });

  return panel;
}

async function _hash(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('').slice(0,16);
}

// ─────────────────────────────────────────────
// Inject CSS
// ─────────────────────────────────────────────
function injectFeedbackCSS() {
  if (document.getElementById('levi-feedback-css')) return;
  const s = document.createElement('style');
  s.id = 'levi-feedback-css';
  s.textContent = `
    .levi-feedback-panel {
      display: flex; align-items: center; gap: 8px;
      margin-top: 8px; padding-top: 8px;
      border-top: 0.5px solid rgba(255,255,255,0.07);
      opacity: 1; max-height: 40px;
      transition: opacity 0.35s ease, max-height 0.35s ease;
      overflow: hidden;
    }
    .levi-feedback-panel.lf-collapsed { opacity: 0; max-height: 0; margin: 0; padding: 0; }
    .lf-label {
      font-size: 10px; color: rgba(105,102,110,0.7);
      text-transform: uppercase; letter-spacing: 0.12em;
      font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 600;
      white-space: nowrap;
    }
    .lf-stars { display: flex; gap: 2px; }
    .lf-star {
      width: 22px; height: 22px; padding: 0;
      background: transparent; border: none; cursor: pointer;
      color: rgba(105,102,110,0.4);
      transition: color 0.15s ease, transform 0.2s cubic-bezier(0.34,1.56,0.64,1);
    }
    .lf-star svg { width: 16px; height: 16px; display: block; }
    .lf-star:hover, .lf-star.lf-hover { color: #f2ca50; transform: scale(1.2); }
    .lf-star.lf-selected { color: #f2ca50; fill: currentColor; }
    .lf-star.lf-selected svg { fill: #f2ca50; }
    .lf-thanks {
      font-size: 10px; color: #f2ca50; opacity: 0;
      font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 600;
      letter-spacing: 0.08em; white-space: nowrap;
      transition: opacity 0.3s ease;
    }
    .lf-thanks.lf-thanks-show { opacity: 1; }
  `;
  document.head.appendChild(s);
}

// ─────────────────────────────────────────────
// Patch: hook into the chat message renderer
// ─────────────────────────────────────────────
function patchChatAppend() {
  injectFeedbackCSS();

  // Override the global appendMsg function defined in chat.html
  const original = window.appendMsg;
  if (typeof original !== 'function') {
    // Try polling for it (chat.html sets it after DOMContentLoaded)
    const wait = setInterval(() => {
      if (typeof window.appendMsg === 'function') {
        clearInterval(wait);
        _doPath();
      }
    }, 100);
    return;
  }
  _doPath();

  function _doPath() {
    const orig = window.appendMsg;
    window.appendMsg = function(content, role) {
      const el = orig.apply(this, arguments);

      if (role === 'bot' && el && content) {
        const sessionId = localStorage.getItem('levi_session_id') || 'anon';
        const lastUser  = _getLastUserMessage();
        const mood      = _getCurrentMood();

        const panel = createFeedbackPanel(lastUser, content, mood, sessionId);
        el.appendChild(panel);

        // Staggered appear
        panel.style.opacity = '0';
        setTimeout(() => { panel.style.opacity = '1'; panel.style.transition = 'opacity 0.4s ease'; }, 800);
      }
      return el;
    };
  }
}

function _getLastUserMessage() {
  const msgs = document.getElementById('messages');
  if (!msgs) return '';
  const userMsgs = msgs.querySelectorAll('.msg-user p');
  return userMsgs.length ? userMsgs[userMsgs.length - 1].textContent : '';
}

function _getCurrentMood() {
  const active = document.querySelector('.mood-chip.active');
  return active ? active.textContent.trim().toLowerCase() : 'philosophical';
}

// ─────────────────────────────────────────────
// Quick-rate button for non-chat pages (studio, quotes)
// ─────────────────────────────────────────────
function createThumbsWidget(userMessage, botResponse, mood, sessionId) {
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:inline-flex;gap:6px;align-items:center;';

  ['👍', '👎'].forEach((emoji, idx) => {
    const btn = document.createElement('button');
    btn.textContent = emoji;
    btn.style.cssText = `
      background: rgba(255,255,255,0.04); border: 0.5px solid rgba(255,255,255,0.08);
      border-radius: 9999px; padding: 4px 10px; cursor: pointer; font-size: 13px;
      transition: all 0.2s; color: inherit;
    `;
    btn.addEventListener('click', async () => {
      const rating = idx === 0 ? 5 : 1;
      btn.style.background = idx === 0 ? 'rgba(242,202,80,0.15)' : 'rgba(248,113,113,0.12)';
      btn.style.borderColor = idx === 0 ? 'rgba(242,202,80,0.4)' : 'rgba(248,113,113,0.3)';

      try {
        await window.waitForToken();
        const token = localStorage.getItem('levi_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        await fetch(`${API_BASE}/feedback`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            session_id: sessionId,
            message_hash: await _hash(userMessage),
            rating, bot_response: botResponse,
            user_message: userMessage, mood, feedback_type: 'thumbs',
          }),
        });
      } catch (e) { console.warn('[LEVI Feedback] Thumbs submit failed:', e); }

      setTimeout(() => { wrap.style.opacity = '0'; setTimeout(() => wrap.remove(), 300); }, 1500);
    });
    wrap.appendChild(btn);
  });

  return wrap;
}

// ─────────────────────────────────────────────
// Auto-init
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  injectFeedbackCSS();
  const page = location.pathname.split('/').pop().replace('.html','');
  if (page === 'chat' || page === '') {
    patchChatAppend();
  }
});

export { createFeedbackPanel, createThumbsWidget, patchChatAppend };
