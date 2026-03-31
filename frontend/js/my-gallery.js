/**
 * LEVI Gallery v3.5
 * My Gallery page - Implementation with Centralized API
 */

'use strict';

const $ = id => document.getElementById(id);

function toggleMobileMenu() {
    const m = $('mobile-menu');
    if (m) m.classList.toggle('hidden');
}

function showToast(msg, type = 'success') {
    if (window.api && window.api.showToast) {
        window.api.showToast(msg, type);
    } else {
        alert(msg);
    }
}

function createCard(item, index) {
    const mediaSrc = item.video_url || item.video || item.image_url || item.image || item.image_b64 || '';
    const isVideo = !!(item.video_url || item.video || (typeof mediaSrc === 'string' && mediaSrc.includes('.mp4')));
    const text = (item.text || '').replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    const author = (item.author || 'LEVI-AI').replace(/'/g, '&#39;');
    const mood = item.mood || 'philosophical';

    const mediaHtml = isVideo
        ? `<video src="${mediaSrc}" class="card-img w-full h-full object-cover" loop muted playsinline
            onmouseenter="this.play()" onmouseleave="this.pause()"></video>`
        : `<img src="${mediaSrc}" alt="LEVI Creation" class="card-img w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 bg-zinc-900" loading="lazy"/>`;

    return `
        <article class="gallery-card group relative rounded-2xl overflow-hidden border border-white/5 hover:border-yellow-400/30 transition-all duration-500 animate-in" 
            style="animation-delay:${index * 50}ms">
            <div class="aspect-[9/16] relative overflow-hidden bg-zinc-900">
                ${mediaHtml}
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-70 group-hover:opacity-90 transition-opacity"></div>

                <div class="absolute top-3 left-3">
                    <span class="px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-widest bg-yellow-400/10 border border-yellow-400/20 text-yellow-400">
                        ${isVideo ? '🎬 Video' : '🎨 Image'}
                    </span>
                </div>

                <div class="absolute inset-x-0 bottom-0 p-4 translate-y-2 group-hover:translate-y-0 transition-transform duration-500">
                    ${text ? `<p class="font-serif italic text-xs text-white/90 leading-snug mb-1 line-clamp-3">"${text}"</p>` : ''}
                    <p class="text-[9px] font-bold uppercase tracking-widest text-yellow-400">— ${author}</p>
                </div>

                <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-400"
                    style="background:rgba(0,0,0,0.5);backdrop-filter:blur(4px)">
                    <button onclick="downloadItem('${mediaSrc}','${isVideo ? 'mp4' : 'png'}','${text}')"
                        class="flex items-center gap-2 px-5 py-2.5 rounded-full font-bold uppercase tracking-wider text-xs transition-all hover:scale-105 bg-yellow-400 text-black">
                        <span class="material-symbols-outlined icon-sm">download</span>Download
                    </button>
                    <button onclick="shareItem('${text}','${author}')"
                        class="flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider border border-white/20 text-white/80 hover:text-white hover:border-white/40 transition-all">
                        <span class="material-symbols-outlined icon-sm">share</span>Share
                    </button>
                    <button onclick="visualizeAgain('${text}','${author}','${mood}')"
                        class="flex items-center gap-2 text-[10px] text-yellow-500 hover:text-yellow-400 uppercase tracking-wider transition-colors">
                        <span class="material-symbols-outlined icon-sm">refresh</span>Re-generate
                    </button>
                </div>
            </div>
        </article>
    `;
}

function downloadItem(src, ext, text) {
    if (!src) return;
    const a = document.createElement('a');
    a.href = src;
    a.download = `levi-${Date.now()}.${ext}`;
    a.click();
}

async function shareItem(text, author) {
    const str = `"${text}" — ${author}`;
    if (navigator.share) {
        navigator.share({ title: 'LEVI-AI Wisdom', text: str, url: location.origin });
    } else {
        await navigator.clipboard.writeText(str);
        showToast('Copied to clipboard');
    }
    
    try {
        const d = await window.api.trackShare();
        if (d.rewarded) showToast('🎁 Bonus: +10 credits!');
    } catch (e) { }
}

function visualizeAgain(text, author, mood) {
    localStorage.setItem('levi_studio_prefill', JSON.stringify({ text, author, mood }));
    window.location.href = 'studio.html';
}

async function loadGallery() {
    try {
        const items = await window.api.getMyGallery();
        const grid = $('gallery-grid');
        const count = $('gallery-count');
        const empty = $('empty-state');
        const loading = $('loading-state');

        if (loading) loading.classList.add('hidden');
        
        if (!items || items.length === 0) {
            if (empty) empty.classList.remove('hidden');
            if (count) count.textContent = '0 creations';
            return;
        }

        if (count) count.textContent = `${items.length} creation${items.length !== 1 ? 's' : ''}`;
        if (grid) grid.innerHTML = items.map((item, i) => createCard(item, i)).join('');

    } catch (e) {
        console.error("Gallery failed", e);
        if ($('loading-state')) $('loading-state').classList.add('hidden');
        if ($('empty-state')) $('empty-state').classList.remove('hidden');
    }
}

// Global Exports
window.toggleMobileMenu = toggleMobileMenu;
window.downloadItem = downloadItem;
window.shareItem = shareItem;
window.visualizeAgain = visualizeAgain;

document.addEventListener('DOMContentLoaded', async () => {
    // Initial check
    await loadGallery();
    if (window.syncUser) window.syncUser();
});