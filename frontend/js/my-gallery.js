/**
 * LEVI Gallery v3.0
 * My Gallery page - load user's generated images and videos
 */

'use strict';

// Fixed API_BASE race condition with a lazy-eval getter
function getApiBase() {
    return window.API_BASE || (
        window.location.hostname === 'localhost'
            ? 'http://localhost:8000/api/v1'
            : `${window.location.origin}/api/v1`
    );
}

const $ = id => document.getElementById(id);

function toggleMobileMenu() {
  const m = $('mobile-menu');
  if (m) m.classList.toggle('hidden');
}
window.toggleMobileMenu = toggleMobileMenu;

function showToast(msg, type = 'success') {
  const t = $('toast');
  if (!t) return;
  const bg = type === 'error' ? 'rgba(127,29,29,.9)' : 'rgba(19,19,23,.92)';
  const border = type === 'error' ? 'rgba(248,113,113,.35)' : 'rgba(242,202,80,.35)';
  t.innerHTML = `<div style="background:${bg};border:.5px solid ${border};backdrop-filter:blur(20px);display:flex;align-items:center;gap:10px;padding:10px 20px;border-radius:9999px;box-shadow:0 8px 32px rgba(0,0,0,.5)">
    <span style="font-size:12px;color:#e5e1e7;font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;letter-spacing:.04em">${msg}</span>
  </div>`;
  t.style.cssText = 'position:fixed;bottom:5rem;left:50%;transform:translateX(-50%) translateY(0);opacity:1;z-index:9999;pointer-events:none;transition:all .3s';
  clearTimeout(t._t);
  t._t = setTimeout(() => { if (t) t.style.opacity = '0'; }, 3000);
}
window.showToast = showToast;

function createCard(item, index) {
  const mediaSrc = item.video_url || item.video || item.image_url || item.image || item.image_b64 || '';
  const isVideo = !!(item.video_url || item.video || (typeof mediaSrc === 'string' && mediaSrc.includes('.mp4')));
  const text = (item.text || '').replace(/'/g, '&#39;').replace(/"/g, '&quot;');
  const author = (item.author || 'LEVI-AI').replace(/'/g, '&#39;');
  const mood = item.mood || 'philosophical';

  const mediaHtml = isVideo
    ? `<video src="${mediaSrc}" class="card-img w-full h-full object-cover" loop muted playsinline
        onmouseenter="this.play()" onmouseleave="this.pause()"></video>`
    : mediaSrc
      ? `<img src="${mediaSrc}" alt="LEVI Creation" class="card-img w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 bg-zinc-900" loading="lazy"/>`
      : `<div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-zinc-900 to-zinc-950">
        <span style="font-family:'Material Symbols Outlined';font-size:48px;color:rgba(242,202,80,.2)">image</span>
      </div>`;

  return `
    <article class="gallery-card group relative rounded-2xl overflow-hidden border border-white/5 hover:border-yellow-400/30 transition-all duration-500 animate-in" 
      style="animation-delay:${index * 50}ms">
      <div class="aspect-[9/16] relative overflow-hidden bg-zinc-900">
        ${mediaHtml}
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-70 group-hover:opacity-90 transition-opacity"></div>

        <!-- Type badge -->
        <div class="absolute top-3 left-3">
          <span class="px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-widest"
            style="background:rgba(242,202,80,.15);border:.5px solid rgba(242,202,80,.3);color:#f2ca50">
            ${isVideo ? '🎬 Video' : '🎨 Image'}
          </span>
        </div>

        <!-- Quote overlay -->
        <div class="absolute inset-x-0 bottom-0 p-4 translate-y-2 group-hover:translate-y-0 transition-transform duration-500">
          ${text ? `<p class="font-serif italic text-xs text-white/90 leading-snug mb-1 line-clamp-3">"${text}"</p>` : ''}
          ${author ? `<p class="text-[9px] font-bold uppercase tracking-widest" style="color:#f2ca50">— ${author}</p>` : ''}
        </div>

        <!-- Action buttons (hover reveal) -->
        <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-400"
          style="background:rgba(0,0,0,.5);backdrop-filter:blur(4px)">
          ${mediaSrc ? `
            <button onclick="downloadItem('${mediaSrc}','${isVideo ? 'mp4' : 'png'}','${text}')"
              class="flex items-center gap-2 px-5 py-2.5 rounded-full font-bold uppercase tracking-wider text-xs transition-all hover:scale-105"
              style="background:linear-gradient(135deg,#f2ca50,#d4af37);color:#3c2f00">
              <span style="font-family:'Material Symbols Outlined';font-size:16px">download</span>Download
            </button>
          ` : ''}
          <button onclick="shareItem('${text}','${author}')"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider border border-white/20 text-white/80 hover:text-white hover:border-white/40 transition-all">
            <span style="font-family:'Material Symbols Outlined';font-size:16px">share</span>Share
          </button>
          ${text ? `
            <button onclick="visualizeAgain('${text}','${author}','${mood}')"
              class="flex items-center gap-2 text-[10px] text-yellow-400/60 hover:text-yellow-400 uppercase tracking-wider transition-colors">
              <span style="font-family:'Material Symbols Outlined';font-size:14px">refresh</span>Re-generate
            </button>
          ` : ''}
        </div>
      </div>
    </article>
  `;
}

function downloadItem(src, ext, text) {
  if (!src) { showToast('No file to download', 'warning'); return; }
  const a = document.createElement('a');
  a.href = src;
  a.download = `levi-${Date.now()}.${ext}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast('Downloading…');
}
window.downloadItem = downloadItem;

async function shareItem(text, author) {
  const str = text ? `"${text}" — ${author}` : `Made with LEVI-AI`;
  if (navigator.share) {
    navigator.share({ title: 'LEVI-AI Wisdom', text: str, url: location.origin });
  } else {
    navigator.clipboard.writeText(str).then(() => showToast('Copied!'));
  }

  const token = await window.waitForToken();
  if (token) {
    fetch(`${getApiBase()}/analytics/track_share`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    }).then(r => r.json()).then(d => {
      if (d.rewarded) showToast('🎁 Share bonus: +10 credits!');
    }).catch(() => { });
  }
}
window.shareItem = shareItem;

function visualizeAgain(text, author, mood) {
  localStorage.setItem('levi_studio_prefill', JSON.stringify({ text, author, mood }));
  window.location.href = 'studio.html';
}
window.visualizeAgain = visualizeAgain;

function logout() {
  firebase.auth().signOut().then(() => {
    localStorage.removeItem('levi_user');
    window.location.href = 'index.html';
  });
}
window.logout = logout;

async function loadGallery() {
  const loadingState = $('loading-state');
  const emptyState = $('empty-state');
  const grid = $('gallery-grid');
  const galleryCount = $('gallery-count');

  const token = await window.waitForToken();
  if (!token) {
    if (loadingState) loadingState.classList.add('hidden');
    if (emptyState) emptyState.classList.remove('hidden');
    if (galleryCount) galleryCount.textContent = 'Sign in to view your gallery';
    return;
  }

  try {
    const res = await fetch(`${getApiBase()}/gallery/my_gallery`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });

    if (loadingState) loadingState.classList.add('hidden');

    if (res.status === 401) {
      if (emptyState) emptyState.classList.remove('hidden');
      if (galleryCount) galleryCount.textContent = 'Session expired — please sign in';
      return;
    }

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const items = await res.json();

    if (!items || !items.length) {
      if (emptyState) emptyState.classList.remove('hidden');
      if (galleryCount) galleryCount.textContent = '0 creations';
      return;
    }

    if (galleryCount) galleryCount.textContent = `${items.length} creation${items.length !== 1 ? 's' : ''}`;

    if (grid) {
      grid.innerHTML = items.map((item, i) => createCard(item, i)).join('');
    }

  } catch (err) {
    if (loadingState) loadingState.classList.add('hidden');
    if (emptyState) emptyState.classList.remove('hidden');
    if (galleryCount) galleryCount.textContent = 'Could not load gallery';
    if (typeof showToast === 'function') showToast("Network error", "error");
    console.error('Gallery load error:', err);
  }
}

function updateNavAuth() {
  const user = JSON.parse(localStorage.getItem('levi_user') || 'null');
  const sidebarUser = $('sidebar-user');
  const creditsEls = document.querySelectorAll('[data-credits]');
  if (user) {
    if (sidebarUser) sidebarUser.textContent = user.username || 'Seeker';
    creditsEls.forEach(el => el.textContent = (user.credits || 0) + ' credits');
  }
}

function injectStyles() {
  const s = document.createElement('style');
  s.textContent = `
    @keyframes fadeUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
    .animate-in { animation: fadeUp .5s ease forwards; opacity:0; }
    .card-img { transition: transform .7s cubic-bezier(.4,0,.2,1); }
    .gallery-card:hover .card-img { transform: scale(1.06); }
  `;
  document.head.appendChild(s);
}

document.addEventListener('DOMContentLoaded', async () => {
  injectStyles();
  updateNavAuth();
  // Ensure we wait for token resolution before initial load
  await window.waitForToken();
  loadGallery();
});