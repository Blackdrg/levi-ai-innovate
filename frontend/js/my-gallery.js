const user = localStorage.getItem('levi_user');
const galleryContainer = document.getElementById('user-gallery');
const emptyState = document.getElementById('empty-state');

if (!user) {
    window.location.href = 'auth.html';
}

function loadGallery() {
    const gallery = JSON.parse(localStorage.getItem(`levi_gallery_${user}`)) || [];

    if (gallery.length === 0) {
        galleryContainer.classList.add('hidden');
        emptyState.classList.remove('hidden');
        return;
    }

    galleryContainer.classList.remove('hidden');
    emptyState.classList.add('hidden');

    galleryContainer.innerHTML = gallery.map((item, index) => `
        <div class="glass-card p-6 rounded-[2rem] flex flex-col gap-6 animate-fade-in-up" style="animation-delay: ${index * 0.1}s">
            <div class="relative group overflow-hidden rounded-2xl">
                <img src="${item.image}" alt="Generated Wisdom" class="w-full h-auto transition-transform duration-500 group-hover:scale-105">
                <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
                    <button onclick="downloadImage('${item.image}', 'levi-art-${item.id}.png')" class="p-3 glass rounded-full hover:bg-white/20 transition-all">📥</button>
                    <button onclick="deleteFromGallery(${item.id})" class="p-3 glass rounded-full hover:bg-red-500/20 transition-all">🗑️</button>
                </div>
            </div>
            <div>
                <p class="text-sm italic font-serif text-muted line-clamp-2">"${item.text}"</p>
                <p class="text-[10px] uppercase tracking-widest text-emerald-400 mt-2">${new Date(item.timestamp).toLocaleDateString()}</p>
            </div>
        </div>
    `).join('');
}

window.downloadImage = (dataUrl, filename) => {
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    link.click();
};

window.deleteFromGallery = (id) => {
    if (!confirm('Are you sure you want to delete this piece from your studio?')) return;
    
    const gallery = JSON.parse(localStorage.getItem(`levi_gallery_${user}`)) || [];
    const newGallery = gallery.filter(item => item.id !== id);
    localStorage.setItem(`levi_gallery_${user}`, JSON.stringify(newGallery));
    loadGallery();
};

loadGallery();
