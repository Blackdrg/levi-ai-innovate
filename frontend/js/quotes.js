import { searchQuotes, generateQuoteImage } from './api.js';

const quotesList = document.getElementById('quotes-list');
const searchInput = document.getElementById('search-input');
const moodButtons = document.querySelectorAll('.mood-btn');

let currentMood = '';

async function loadQuotes(query = '', mood = '') {
    quotesList.innerHTML = `
        <div class="col-span-full text-center py-20">
            <div class="animate-spin w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-muted">Searching the archives...</p>
        </div>
    `;

    try {
        const results = await searchQuotes(query, { mood });
        renderQuotes(results);
    } catch (err) {
        quotesList.innerHTML = `<div class="col-span-full text-center text-red-400">Error loading quotes. Please try again later.</div>`;
        console.error(err);
    }
}

window.loadQuotes = () => loadQuotes(searchInput.value, currentMood);

function renderQuotes(quotes) {
    if (quotes.length === 0) {
        quotesList.innerHTML = `<div class="col-span-full text-center py-20 text-muted text-xl">No quotes found matching your search.</div>`;
        return;
    }

    quotesList.innerHTML = quotes.map((q, index) => `
        <div class="glass-card p-8 rounded-[2rem] flex flex-col justify-between animate-fade-in" style="animation-delay: ${index * 0.1}s">
            <div>
                <div class="text-[10px] font-bold uppercase tracking-widest text-emerald-400 mb-4">${q.topic || 'Wisdom'}</div>
                <p class="text-xl italic font-serif leading-relaxed mb-6">"${q.quote}"</p>
                <p class="text-muted font-medium">— ${q.author || 'Unknown'}</p>
            </div>
            
            <div class="flex gap-3 mt-8 pt-6 border-t border-white/5">
                <button onclick="window.shareQuote('${q.quote.replace(/'/g, "\\'")}')" class="p-2 glass hover:bg-white/10 rounded-xl transition-all" title="Share">📤</button>
                <button onclick="window.generateVisual('${q.quote.replace(/'/g, "\\'")}', '${q.author.replace(/'/g, "\\'")}')" class="p-2 glass hover:bg-violet-500/20 rounded-xl transition-all" title="Generate Art">🎨</button>
                <button onclick="window.speakText('${q.quote.replace(/'/g, "\\'")}')" class="p-2 glass hover:bg-emerald-500/20 rounded-xl transition-all" title="Listen">🔊</button>
                <button onclick="window.likeQuote(this, '${q.quote.replace(/'/g, "\\'")}')" class="p-2 glass hover:bg-pink-500/20 rounded-xl transition-all ml-auto" title="Like">🤍</button>
            </div>
        </div>
    `).join('');
}

// Search with Debounce
let debounceTimer;
searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        loadQuotes(e.target.value, currentMood);
    }, 500);
});

// Mood Filtering
moodButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const mood = btn.dataset.mood;
        if (currentMood === mood) {
            currentMood = '';
            btn.classList.remove('border-primary', 'bg-white/10');
        } else {
            moodButtons.forEach(b => b.classList.remove('border-primary', 'bg-white/10'));
            currentMood = mood;
            btn.classList.add('border-primary', 'bg-white/10');
        }
        loadQuotes(searchInput.value, currentMood);
    });
});

// Reuse global actions from window if needed or redefine
window.shareQuote = (text) => {
    if (navigator.share) {
        navigator.share({ title: 'LEVI Wisdom', text }).catch(console.error);
    } else {
        window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
    }
};

window.speakText = (text) => {
    const synth = window.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    synth.speak(utterance);
};

window.generateVisual = async (text, author, mood = "") => {
    // Re-use logic from chat.js for visual generation
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/90 backdrop-blur-xl flex items-center justify-center z-[100] animate-fade-in p-6';
    modal.innerHTML = `
      <div class="glass-card p-8 rounded-[2.5rem] max-w-lg w-full text-center relative">
        <button onclick="this.parentElement.parentElement.remove()" class="absolute top-4 right-4 text-muted hover:text-white">✕</button>
        <div id="visual-loading" class="py-12">
            <div class="animate-spin w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-muted">Painting your inspiration...</p>
        </div>
        <div id="visual-result" class="hidden">
            <div class="relative group mb-6">
                <img id="generated-img" src="" alt="Artistic Quote" class="w-full h-auto rounded-2xl shadow-2xl">
                <!-- Creative Director Controls -->
                <div id="editor-controls" class="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="window.updateArtStyle('grayscale(1)')" class="glass p-2 rounded-full text-xs">⚫</button>
                    <button onclick="window.updateArtStyle('sepia(0.5)')" class="glass p-2 rounded-full text-xs">🟤</button>
                    <button onclick="window.updateArtStyle('hue-rotate(90deg)')" class="glass p-2 rounded-full text-xs">🌈</button>
                    <button onclick="window.updateArtStyle('none')" class="glass p-2 rounded-full text-xs">🔄</button>
                </div>
            </div>
            <div class="flex flex-col gap-4">
                <div class="flex gap-4">
                    <div class="relative flex-1 group">
                        <button id="download-btn" class="btn-primary w-full py-3 rounded-xl">Download</button>
                        <!-- Resolution Menu -->
                        <div class="absolute bottom-full mb-2 left-0 w-full glass rounded-xl overflow-hidden hidden group-hover:block border border-white/10">
                            <button onclick="window.downloadRes(1080, 1920)" class="w-full p-2 text-[10px] hover:bg-white/5 text-left border-b border-white/5">📱 Phone (9:16)</button>
                            <button onclick="window.downloadRes(1920, 1080)" class="w-full p-2 text-[10px] hover:bg-white/5 text-left border-b border-white/5">💻 Desktop (16:9)</button>
                            <button onclick="window.downloadRes(1080, 1080)" class="w-full p-2 text-[10px] hover:bg-white/5 text-left">🔳 Square (1:1)</button>
                        </div>
                    </div>
                    <button id="save-btn" class="glass px-6 py-3 rounded-xl flex-1 hover:bg-white/5 transition-all">Save to Studio</button>
                </div>
                <button onclick="this.parentElement.parentElement.parentElement.parentElement.remove()" class="text-xs text-muted hover:text-white transition-colors">Close</button>
            </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    try {
        const { generateQuoteImage } = await import('./api.js');
        const data = await generateQuoteImage(text, author, mood);
        const img = document.getElementById('generated-img');
        img.src = data.image_b64;
        document.getElementById('visual-loading').classList.add('hidden');
        document.getElementById('visual-result').classList.remove('hidden');
        
        document.getElementById('download-btn').onclick = () => {
            const link = document.createElement('a');
            link.href = img.src;
            link.download = 'levi-art.png';
            link.click();
        };

        document.getElementById('save-btn').onclick = (e) => {
          const user = localStorage.getItem('levi_user');
          if (!user) {
            alert("Please login to save art to your studio!");
            window.location.href = 'auth.html';
            return;
          }
          const gallery = JSON.parse(localStorage.getItem(`levi_gallery_${user}`)) || [];
          gallery.unshift({
            id: Date.now(),
            image: data.image_b64,
            text: text,
            timestamp: new Date().toISOString()
          });
          localStorage.setItem(`levi_gallery_${user}`, JSON.stringify(gallery));
          e.target.innerText = 'Saved! ✨';
          e.target.disabled = true;
          e.target.classList.add('opacity-50');
        };

        window.updateArtStyle = (filter) => {
            document.getElementById('generated-img').style.filter = filter;
        };

        window.downloadRes = async (w, h) => {
            const img = document.getElementById('generated-img');
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = "#050B14";
            ctx.fillRect(0, 0, w, h);
            const scale = Math.max(w / img.naturalWidth, h / img.naturalHeight);
            const x = (w / 2) - (img.naturalWidth / 2) * scale;
            const y = (h / 2) - (img.naturalHeight / 2) * scale;
            ctx.filter = img.style.filter;
            ctx.drawImage(img, x, y, img.naturalWidth * scale, img.naturalHeight * scale);
            const link = document.createElement('a');
            link.href = canvas.toDataURL('image/png');
            link.download = `levi-wallpaper-${w}x${h}.png`;
            link.click();
        };

    } catch (err) {
        modal.remove();
        alert("Failed to generate visual. Please try again.");
    }
};

// Initial Load
loadQuotes();

