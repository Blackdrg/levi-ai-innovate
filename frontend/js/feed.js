// feed.js - Dynamic Community Feed for LEVI AI
document.addEventListener('DOMContentLoaded', loadFeed);

async function loadFeed() {
    const grid = document.querySelector('.masonry-grid');
    if (!grid) return;

    // Show initial loading placeholders if needed, or clear static ones
    grid.innerHTML = '';
    
    try {
        await window.waitForToken();
        const data = await window.api.getFeed(15);
        const items = data.items || data;

        if (!items || items.length === 0) {
            grid.innerHTML = '<div class="col-span-full py-20 text-center text-zinc-500 italic">The celestial archives are quiet today.</div>';
            return;
        }

        items.forEach(item => {
            const card = document.createElement('article');
            const type = item.type || "image";
            const aspectRatio = item.aspect_ratio || "1:1";
            
            // Map 9:16, 16:9, 1:1 etc to Tailwind classes
            const aspectClass = aspectRatio.includes(':') ? `aspect-[${aspectRatio.replace(':', '/')}]` : 'aspect-[3/4]';
            
            card.className = `break-inside-avoid mb-8 group relative rounded-2xl overflow-hidden glass-card border border-white/5 hover:border-primary/30 transition-all duration-500 fade-in`;
            
            const mediaUrl = type === "video" ? (item.video || item.image) : (item.image || item.video);
            const text = item.text || item.quote || "A silent thought.";
            const author = item.author || "Anonymous Seeker";
            const likes = item.likes || 0;

            let mediaHtml = "";
            if (type === "video") {
                mediaHtml = `
                    <video src="${mediaUrl}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" 
                           autoplay muted loop playsinline loading="lazy"></video>
                `;
            } else {
                mediaHtml = `
                    <img src="${mediaUrl}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" loading="lazy" />
                `;
            }

            card.innerHTML = `
                <div class="relative overflow-hidden ${aspectClass}">
                    ${mediaHtml}
                    <div class="absolute inset-0 bg-gradient-to-t from-black via-black/20 to-transparent opacity-60"></div>
                    ${type === 'video' ? '<div class="absolute top-4 right-4 bg-black/40 backdrop-blur-md px-2 py-1 rounded text-[10px] font-bold text-white/80 uppercase tracking-tighter">Cinematic</div>' : ''}
                </div>
                <div class="absolute inset-0 flex flex-col justify-end p-8 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-black/60 backdrop-blur-sm">
                    <span class="material-symbols-outlined text-primary text-4xl mb-4">format_quote</span>
                    <blockquote class="font-headline text-xl text-on-surface leading-tight italic mb-4 line-clamp-4">
                        "${text}"
                    </blockquote>
                    <cite class="not-italic font-label text-[10px] uppercase tracking-widest text-primary font-bold mb-6">— ${author}</cite>
                    <div class="flex items-center justify-between border-t border-white/10 pt-6">
                        <div class="flex items-center gap-4">
                            <button onclick="likeItem('${item.id}', this)" class="flex items-center gap-1.5 text-zinc-300 hover:text-emerald-400 transition-colors">
                                <span class="material-symbols-outlined text-lg">favorite</span>
                                <span class="text-xs font-bold">${likes}</span>
                            </button>
                            <button onclick="shareItem('${item.id}', '${text.replace(/'/g, "\\'")}')" class="flex items-center gap-1.5 text-zinc-300 hover:text-primary transition-colors">
                                <span class="material-symbols-outlined text-lg">share</span>
                            </button>
                        </div>
                        <a href="studio.html?quote=${encodeURIComponent(text)}&author=${encodeURIComponent(author)}&aspect=${aspectRatio}" class="text-[10px] font-bold text-zinc-400 hover:text-primary flex items-center gap-1 uppercase tracking-widest">
                            Remix <span class="material-symbols-outlined text-sm">edit_note</span>
                        </a>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (e) {
        console.error("[LEVI] Feed load failed:", e);
        if (window.ui && window.ui.showToast) window.ui.showToast("Failed to sync with the collective consciousness.", "error");
    }
}

async function likeItem(id, btn) {
    try {
        await window.api.likeItem('feed', id);
        btn.classList.add('text-emerald-400');
        const count = btn.querySelector('span:last-child');
        if (count) count.textContent = parseInt(count.textContent) + 1;
        if (window.ui && window.ui.showToast) window.ui.showToast("Echo saved to your soul.");
    } catch (e) {
        console.error("Like failed:", e);
    }
}

async function shareItem(id, text) {
    if (navigator.share) {
        navigator.share({ title: 'LEVI AI Wisdom', text: text, url: window.location.origin + '/feed.html?id=' + id });
    } else {
        await navigator.clipboard.writeText(text);
        if (window.ui && window.ui.showToast) window.ui.showToast("Wisdom copied to clipboard.");
    }
}

window.likeItem = likeItem;
window.shareItem = shareItem;
