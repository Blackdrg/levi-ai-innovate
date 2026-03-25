/**
 * LEVI Studio v2.0
 * Uses cookie-based auth via credentials:'include'.
 */

function toggleMobileMenu() {
  const m = document.getElementById('mobile-menu');
  if (m) { m.classList.toggle('hidden'); document.body.style.overflow = m.classList.contains('hidden') ? '' : 'hidden'; }
}

function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  if (!t) return;
  const bg     = type === 'error' ? 'rgba(147,0,10,.85)' : type === 'warning' ? 'rgba(120,90,0,.85)' : 'rgba(19,19,23,.9)';
  const border = type === 'error' ? 'rgba(255,180,171,.3)' : type === 'warning' ? 'rgba(242,202,80,.4)' : 'rgba(242,202,80,.35)';
  const icon   = type === 'error' ? 'error' : type === 'warning' ? 'warning' : 'check_circle';
  t.innerHTML  = `<div style="background:${bg};border:.5px solid ${border};backdrop-filter:blur(20px);border-radius:9999px;padding:10px 20px;box-shadow:0 8px 32px rgba(0,0,0,.5);display:flex;align-items:center;gap:10px">
    <span class="material-symbols-outlined icon-fill" style="font-size:16px;color:#f2ca50">${icon}</span>
    <span style="font-size:12px;color:#e5e1e7;font-weight:600;letter-spacing:.04em">${msg}</span>
  </div>`;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 3200);
}

// ── API base (set by auth-manager or inline) ──────────────────────────────────
const _API = window.API_BASE ||
  (['localhost','127.0.0.1','::1','0.0.0.0'].includes(location.hostname)
    ? `http://${location.hostname}:8000`
    : `${location.origin}/api`);

window.API_BASE = _API;

// ── State ─────────────────────────────────────────────────────────────────────
let currentStyle  = 'philosophical';
let currentImage  = null;

const INSIGHTS = {
  philosophical: { text: 'prioritize ethereal lighting, high-contrast obsidian shadows, and golden particle dispersion.',  stability: 67 },
  zen:           { text: 'evoke bamboo mist, still water reflections, and morning light through ancient forests.',          stability: 82 },
  cyberpunk:     { text: 'generate neon-soaked cityscapes, rain-slicked streets, and holographic overlays.',               stability: 74 },
  futuristic:    { text: 'render clean white surfaces, cosmic voids, and geometric precision with bioluminescent accents.', stability: 91 },
  stoic:         { text: 'depict marble columns, dawn light, classical architecture — austere and powerful.',               stability: 88 },
  melancholic:   { text: 'create rain-washed cobblestones, blue hour, soft bokeh with poetic melancholy.',                 stability: 79 },
};

// ── Char counter ──────────────────────────────────────────────────────────────
function updateChar(el) {
  const n  = el.value.length;
  const cc = document.getElementById('char-count');
  if (cc) { cc.textContent = n; cc.style.color = n > 260 ? '#f87171' : n > 200 ? '#f2ca50' : ''; }
}

// ── Style selector ────────────────────────────────────────────────────────────
function setStyle(btn, style) {
  document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentStyle = style;

  const info = INSIGHTS[style] || INSIGHTS.philosophical;
  const name = style.charAt(0).toUpperCase() + style.slice(1);
  const iEl  = document.getElementById('insight-text');
  const sBar = document.getElementById('stability-bar');
  const sVal = document.getElementById('stability-val');
  if (iEl)  iEl.innerHTML = `Synthesizing with <span class="text-primary italic">${name}</span> style will ${info.text}`;
  if (sBar) sBar.style.width = info.stability + '%';
  if (sVal) sVal.textContent = info.stability + '%';
}

// ── Quick-fill ────────────────────────────────────────────────────────────────
function prefill(text, author, style) {
  const wi = document.getElementById('wisdom-input');
  const ai = document.getElementById('author-input');
  if (wi) { wi.value = text; updateChar(wi); }
  if (ai) ai.value = author;
  const btn = document.querySelector(`.style-btn[onclick*="${style}"]`);
  if (btn) setStyle(btn, style);
  showToast('Prefilled: ' + author);
}
window.prefill = prefill;

// ── Loading state ─────────────────────────────────────────────────────────────
function setLoading(on) {
  const icon    = document.getElementById('synth-icon');
  const spinner = document.getElementById('synth-spinner');
  const btn     = document.getElementById('synth-btn');
  const overlay = document.getElementById('loading-overlay');
  const ph      = document.getElementById('preview-placeholder');
  const hud     = document.getElementById('hud-label');
  if (icon)    icon.classList.toggle('hidden', on);
  if (spinner) spinner.classList.toggle('hidden', !on);
  if (btn)     btn.disabled = on;
  if (overlay) overlay.classList.toggle('hidden', !on);
  if (ph)      ph.classList.toggle('hidden', on);
  if (hud)     hud.textContent = on ? 'Synthesizing' : 'Ready';
}

// ── Image display ─────────────────────────────────────────────────────────────
function displayImage(src, text) {
  currentImage = src;
  const img  = document.getElementById('preview-img');
  const con  = document.getElementById('preview-container');
  const ph   = document.getElementById('preview-placeholder');
  const bot  = document.getElementById('preview-bottom-overlay');
  const ptit = document.getElementById('preview-title');
  const vBtn = document.getElementById('video-btn');

  if (img)  { img.src = src; img.onload = () => img.classList.remove('opacity-0'); }
  if (con)  con.classList.remove('hidden');
  if (ph)   ph.classList.add('hidden');
  if (bot)  bot.style.opacity = '1';
  if (ptit) ptit.textContent = text.length > 42 ? text.slice(0, 42) + '…' : text;
  if (vBtn) vBtn.disabled = false;

  addThumb(src);
  showToast('Masterpiece rendered ✦');
}

function addThumb(src) {
  const strip = document.getElementById('thumb-strip');
  if (!strip) return;
  const div = document.createElement('div');
  div.className = 'thumb selected flex-shrink-0 w-24 h-24 rounded-2xl overflow-hidden border-2 cursor-pointer';
  div.onclick = () => {
    const img = document.getElementById('preview-img');
    if (img) img.src = src;
    document.querySelectorAll('.thumb').forEach(t => t.classList.remove('selected'));
    div.classList.add('selected');
  };
  div.innerHTML = `<img src="${src}" class="w-full h-full object-cover"/>`;
  const newBtn = strip.querySelector('button');
  strip.insertBefore(div, newBtn);
  document.querySelectorAll('.thumb').forEach(t => t.classList.remove('selected'));
  div.classList.add('selected');
}

// ── Task polling ──────────────────────────────────────────────────────────────
async function pollTask(taskId, quoteText) {
  let retries = 0;
  const MAX = 60;
  let interval = 2000;

  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.remove('hidden');

  const check = async () => {
    try {
      const res  = await fetch(`${_API}/task_status/${taskId}`, { credentials: 'include' });
      const data = await res.json();

      if (data.status === 'completed' && data.result) {
        const url = data.result.url || data.result.image_b64 || data.result;
        setLoading(false);
        if (overlay) overlay.classList.add('hidden');
        displayImage(url, quoteText);
      } else if (data.status === 'failed') {
        setLoading(false);
        if (overlay) overlay.classList.add('hidden');
        showToast('Synthesis failed — please try again.', 'error');
      } else {
        retries++;
        if (retries >= MAX) { setLoading(false); if (overlay) overlay.classList.add('hidden'); showToast('Timeout — try again.', 'error'); return; }
        interval = Math.min(interval * 1.15, 8000);
        setTimeout(check, interval);
      }
    } catch {
      setTimeout(check, 5000);
    }
  };
  check();
}

// ── Demo fallback ─────────────────────────────────────────────────────────────
function displayDemo(text) {
  const cv  = document.createElement('canvas');
  cv.width  = 512; cv.height = 512;
  const ctx = cv.getContext('2d');
  const palettes = {
    philosophical: ['#0a0a18','#1a1040'], zen: ['#081210','#0f2820'],
    cyberpunk: ['#0a0018','#200040'],     futuristic: ['#080c18','#0c1e38'],
    stoic: ['#0e0c0a','#20201a'],         melancholic: ['#080c14','#0c1828'],
  };
  const p = palettes[currentStyle] || palettes.philosophical;
  const g = ctx.createLinearGradient(0, 0, 512, 512);
  g.addColorStop(0, p[0]); g.addColorStop(1, p[1]);
  ctx.fillStyle = g; ctx.fillRect(0, 0, 512, 512);
  ctx.strokeStyle = 'rgba(242,202,80,.2)'; ctx.lineWidth = 1; ctx.strokeRect(16, 16, 480, 480);
  ctx.fillStyle = 'rgba(242,202,80,.7)'; ctx.font = 'italic 18px serif'; ctx.textAlign = 'center';
  const words = text.split(' ');
  let lines = [], line = '';
  for (const w of words) {
    const t = line + (line ? ' ' : '') + w;
    if (ctx.measureText(t).width > 420) { lines.push(line); line = w; } else line = t;
  }
  lines.push(line);
  const sy = 256 - (lines.length * 28) / 2;
  lines.forEach((l, i) => ctx.fillText(l, 256, sy + i * 28));
  displayImage(cv.toDataURL(), text);
}

// ── Main synthesize ────────────────────────────────────────────────────────────
async function synthesize() {
  const text   = document.getElementById('wisdom-input')?.value.trim();
  const author = document.getElementById('author-input')?.value.trim() || 'LEVI AI';
  const bg     = document.getElementById('bg-input')?.value.trim() || '';

  if (!text) { showToast('Enter some wisdom first', 'error'); return; }

  setLoading(true);

  try {
    const res  = await fetch(`${_API}/generate_image`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, author, mood: currentStyle, background: bg }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();

    if (data.task_id) {
      setLoading(false);
      showToast('Synthesis queued — generating…');
      pollTask(data.task_id, text);
      return;
    }

    if (data.image_url || data.image_b64) {
      displayImage(data.image_url || data.image_b64, text);
    } else {
      throw new Error('No image in response');
    }

  } catch (err) {
    console.warn('[Studio] synthesize error:', err);
    showToast('Showing demo preview (backend offline or error)', 'warning');
    displayDemo(text);
  } finally {
    setLoading(false);
  }
}

function downloadImg() {
  if (!currentImage) return;
  const a = document.createElement('a');
  a.href = currentImage; a.download = `levi-${Date.now()}.png`; a.click();
  showToast('Downloading…');
}

function shareImg() {
  const t = document.getElementById('wisdom-input')?.value || '';
  if (navigator.share) { navigator.share({ title: 'LEVI AI Wisdom', text: t, url: location.href }); }
  else { navigator.clipboard.writeText(t); showToast('Quote copied to clipboard'); }
}

function regenerate() {
  const wi = document.getElementById('wisdom-input');
  if (wi?.value.trim()) synthesize();
}

function makeVideo() { showToast('Video generation queued — check My Gallery'); }

function newCanvas() {
  currentImage = null;
  const con  = document.getElementById('preview-container');
  const ph   = document.getElementById('preview-placeholder');
  const bot  = document.getElementById('preview-bottom-overlay');
  const vBtn = document.getElementById('video-btn');
  const wi   = document.getElementById('wisdom-input');
  const ai   = document.getElementById('author-input');
  if (con)  con.classList.add('hidden');
  if (ph)   ph.classList.remove('hidden');
  if (bot)  bot.style.opacity = '';
  if (vBtn) vBtn.disabled = true;
  if (wi)   { wi.value = ''; updateChar(wi); }
  if (ai)   ai.value = '';
  const hud = document.getElementById('hud-label');
  if (hud) hud.textContent = 'Awaiting';
}

// ── Auth UI init ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const user = (() => { try { return JSON.parse(localStorage.getItem('levi_user') || 'null'); } catch { return null; } })();
  if (user) {
    const uName  = document.getElementById('user-name');
    const uAvt   = document.getElementById('user-avatar');
    const navBtn = document.getElementById('nav-auth-btn');
    if (uName) uName.textContent  = user.username || 'Seeker';
    if (uAvt)  uAvt.textContent   = (user.username || 'S').charAt(0).toUpperCase();
    if (navBtn) { navBtn.textContent = user.username || 'Account'; navBtn.onclick = () => { window.location.href = 'my-gallery.html'; }; }
    document.querySelectorAll('[data-credits]').forEach(el => { el.textContent = (user.credits || 0) + ' credits'; });
  }

  // Check URL prefill from quotes page
  const pf = new URLSearchParams(location.search);
  if (pf.has('quote')) {
    const wi = document.getElementById('wisdom-input');
    if (wi) { wi.value = decodeURIComponent(pf.get('quote')); updateChar(wi); }
  }
});

// Expose
window.updateChar  = updateChar;
window.setStyle    = setStyle;
window.synthesize  = synthesize;
window.downloadImg = downloadImg;
window.shareImg    = shareImg;
window.regenerate  = regenerate;
window.makeVideo   = makeVideo;
window.newCanvas   = newCanvas;
window.toggleMobileMenu = toggleMobileMenu;
window.showToast   = showToast;
