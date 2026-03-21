/**
 * my-gallery.js — Personal gallery page.
 * Loads images saved from Studio via localStorage.
 */

const grid = document.getElementById('gallery-grid');

function renderGallery() {
    const user = localStorage.getItem('levi_user');

    if (!user) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-20 glass rounded-[2rem] border border-white/5">
                <p class="text-slate-500 italic mb-4">Please sign in to view your gallery.</p>
                <a href="auth.html" class="inline-block px-8 py-3 bg-gold text-space font-bold rounded-xl hover:scale-105 transition-transform">
                    Sign In
                </a>
            </div>`;
        return;
    }

    const galleryKey = `levi_gallery_${user}`;
    const items = JSON.parse(localStorage.getItem(galleryKey) || '[]');

    if (items.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-20 glass rounded-[2rem] border border-white/5">
                <p class="text-slate-500 italic mb-4">No masterpieces yet. Start creating in the Studio!</p>
                <a href="studio.html" class="inline-block px-8 py-3 bg-gold text-space font-bold rounded-xl hover:scale-105 transition-transform">
                    Go to Studio
                </a>
            </div>`;
        return;
    }

    grid.innerHTML = '';

    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'glass rounded-[2rem] border border-white/10 overflow-hidden group relative';

        const dateStr = item.timestamp
            ? new Date(item.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
            : '';

        card.innerHTML = `
            <!-- Image -->
            <div class="aspect-square overflow-hidden relative">
                <img
                    src="${item.image}"
                    alt="Gallery image"
                    class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                    onerror="this.src='https://via.placeholder.com/400x400/09090f/d4af37?text=LEVI'"
                >
                <!-- Hover overlay -->
                <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
                    <button
                        onclick="downloadItem(${index})"
                        class="p-3 bg-white/10 backdrop-blur-md rounded-xl hover:bg-white/20 transition-all"
                        title="Download"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                    </button>
                    <button
                        onclick="deleteItem(${index})"
                        class="p-3 bg-red-500/20 backdrop-blur-md rounded-xl hover:bg-red-500/40 transition-all"
                        title="Delete"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Caption -->
            <div class="p-6">
                <p class="font-display text-lg italic text-slate-200 mb-2 leading-snug line-clamp-2">
                    "${item.text || 'Untitled'}"
                </p>
                <span class="text-[10px] font-bold tracking-widest uppercase text-slate-500">${dateStr}</span>
            </div>
        `;

        grid.appendChild(card);
    });
}

// ── Download ──────────────────────────────────────────────────────────────────
window.downloadItem = function (index) {
    const user  = localStorage.getItem('levi_user');
    const items = JSON.parse(localStorage.getItem(`levi_gallery_${user}`) || '[]');
    const item  = items[index];
    if (!item) return;

    const a = document.createElement('a');
    a.href     = item.image;
    a.download = `levi-${Date.now()}.png`;
    a.click();
};

// ── Delete ────────────────────────────────────────────────────────────────────
window.deleteItem = function (index) {
    if (!confirm('Remove this creation from your gallery?')) return;

    const user    = localStorage.getItem('levi_user');
    const galleryKey = `levi_gallery_${user}`;
    const items   = JSON.parse(localStorage.getItem(galleryKey) || '[]');
    items.splice(index, 1);
    localStorage.setItem(galleryKey, JSON.stringify(items));
    renderGallery();
};

// ── Init ──────────────────────────────────────────────────────────────────────
renderGallery();

// Update nav auth button
const navBtn = document.getElementById('nav-auth-btn');
if (navBtn) {
    const user = localStorage.getItem('levi_user');
    if (user) {
        navBtn.textContent = user;
        navBtn.href = 'my-gallery.html';
    }
}
