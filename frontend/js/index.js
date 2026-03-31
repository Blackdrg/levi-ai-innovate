// index.js
// Production Hardened Landing Page Logic

// 1. Stats Animation
async function loadStats() {
    try {
        const data = await window.api.getStatus();
        if (data) {
            animateValue("stat-quotes", 0, data.knowledge_base_entries || 1240, 2000);
            animateValue("stat-artists", 0, data.training_samples || 542, 2000);
            animateValue("stat-uptime", 0, 99.9, 2000, "%");
        }
    } catch (err) {
        console.warn("Analytics failed, using defaults");
        animateValue("stat-quotes", 0, 1240, 1000);
        animateValue("stat-artists", 0, 542, 1000);
        animateValue("stat-uptime", 0, 99, 1000, "%");
    }
}

function animateValue(id, start, end, duration, suffix = "") {
    const obj = document.getElementById(id);
    if (!obj) return;
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start).toLocaleString() + suffix;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
loadStats();

// 3. Daily Wisdom
async function loadDaily() {
    const quoteEl = document.getElementById('daily-quote');
    const authorEl = document.getElementById('daily-author');
    const categoryEl = document.getElementById('daily-category');
    try {
        const data = await window.api.apiFetch("/daily_quote");
        if (data) {
            quoteEl.textContent = `"${data.text}"`;
            authorEl.textContent = data.author || "LEVI-AI";
            categoryEl.textContent = data.topic || "Philosophical";
        }
    } catch (err) {
        console.warn('Daily quote failed');
    }
}
loadDaily();

// 4. Chat Demo Logic
const chatInput = document.querySelector('#chat-demo input');
const chatBtn = document.querySelector('#chat-demo button[aria-label="Send Message"]');
const chatMessages = document.getElementById('chat-messages');
const typingIndicator = document.getElementById('typing-indicator');
const clearChatBtn = document.getElementById('clear-chat');
let currentLang = 'en';

// Lang toggle
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.onclick = () => {
        document.querySelectorAll('.lang-btn').forEach(b => {
            b.classList.remove('bg-gold', 'text-space', 'active');
            b.classList.add('bg-white/5', 'text-slate-400');
        });
        btn.classList.add('bg-gold', 'text-space', 'active');
        btn.classList.remove('bg-white/5', 'text-slate-400');
        currentLang = btn.dataset.lang;
        localStorage.setItem('levi_lang', currentLang);
    };
});

async function handleChat() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    // User Message
    appendMessage(msg, 'user');
    chatInput.value = '';

    // Show typing
    typingIndicator.classList.remove('opacity-0');
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        let botFullText = "";
        const botDiv = document.createElement('div');
        botDiv.className = "flex justify-start";
        const inner = document.createElement('div');
        inner.className = "glass px-5 py-3 rounded-2xl rounded-tl-none max-w-[80%] text-sm border-white/5 whitespace-pre-wrap";
        botDiv.appendChild(inner);
        chatMessages.insertBefore(botDiv, typingIndicator);

        await window.api.chatStream(
            msg, 
            "demo-session", 
            (chunk) => {
                botFullText += chunk;
                inner.textContent = botFullText;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            },
            (meta) => { console.log("[Demo] Meta:", meta); }
        );
        
        typingIndicator.classList.add('opacity-0');
        if (window.syncUser) window.syncUser();
    } catch (err) {
        typingIndicator.classList.add('opacity-0');
        appendMessage("The connection to the cosmic archive was interrupted.", 'bot');
    }
}

function appendMessage(text, side) {
    const div = document.createElement('div');
    div.className = `flex ${side === 'user' ? 'justify-end' : 'justify-start'}`;
    const inner = document.createElement('div');
    inner.className = side === 'user'
        ? "bg-gold text-space px-5 py-3 rounded-2xl rounded-tr-none max-w-[80%] text-sm font-medium"
        : "glass px-5 py-3 rounded-2xl rounded-tl-none max-w-[80%] text-sm border-white/5";
    inner.textContent = text;
    div.appendChild(inner);
    chatMessages.insertBefore(div, typingIndicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatBtn.onclick = handleChat;
chatInput.onkeypress = (e) => { if (e.key === 'Enter') handleChat(); };

clearChatBtn.onclick = () => {
    const messages = chatMessages.querySelectorAll('div:not(#typing-indicator)');
    messages.forEach(m => m.remove());
    appendMessage("Cosmic history cleared. Ready for a new journey.", 'bot');
};

// 5. Search Debounce
const searchInput = document.querySelector('#hero input');
let searchTimeout;
if (searchInput) {
    searchInput.oninput = () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const query = searchInput.value.trim();
            if (query.length > 3) {
                console.log(`Searching for: ${query}`);
            }
        }, 500);
    };
}

// Keyboard Shortcut Ctrl+K
window.onkeydown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
    }
};

// 6. Gallery & Feed
async function loadGallery() {
    const galleryGrid = document.querySelector('#gallery .grid');
    if (!galleryGrid) return;
    try {
        const data = await window.api.getFeed(2);
        const items = data.items || data;
        if (items && items.length > 0) {
            const cards = galleryGrid.querySelectorAll('.group');
            items.forEach((item, i) => {
                if (cards[i]) {
                    const img = cards[i].querySelector('img');
                    const quote = cards[i].querySelector('.font-display');
                    const author = cards[i].querySelector('.text-gold');
                    const likeBtn = cards[i].querySelector('button');

                    const url = item.url || item.image_url || item.image_b64;
                    if (img) img.src = url;
                    if (quote) quote.textContent = `"${item.text || item.quote}"`;
                    if (author) author.textContent = item.author || "Anonymous Seeker";

                    if (likeBtn) {
                        likeBtn.onclick = async () => {
                            try {
                                await window.api.likeItem('feed', item.id);
                                likeBtn.classList.add('text-pink-500');
                            } catch (err) { console.error(err); }
                        };
                    }
                }
            });
        }
    } catch (err) {
        console.warn("Gallery feed failed", err);
    }
}
loadGallery();

async function loadMoreFeed() {
    window.location.href = 'feed.html';
}
document.getElementById('view-all-feed').onclick = loadMoreFeed;

document.querySelector('#gallery .border-dashed').onclick = () => {
    window.location.href = 'studio.html';
};

// 7. Scroll Effects
// 8. Phase 44: Real-Time Cosmic Activity Ticker
function initCosmicStream() {
    // Phase 4: Init Ticker
    let tickerContainer = document.getElementById('cosmic-ticker');
    if (!tickerContainer) {
        tickerContainer = document.createElement('div');
        tickerContainer.id = 'cosmic-ticker';
        tickerContainer.className = 'fixed bottom-24 right-6 z-[60] flex flex-col gap-3 pointer-events-none';
        document.body.appendChild(tickerContainer);
    }

    if (typeof EventSource === 'undefined') return;

    const streamUrl = `${window.API_BASE.replace('/v1', '')}/v1/stream`;
    let source = new EventSource(streamUrl);
    let reconnectTimeout = null;

    const connect = () => {
        if (source) source.close();
        source = new EventSource(streamUrl);
        
        source.onmessage = (event) => {
            // Phase 4: Handle Heartbeats (ignore comments/empty messages)
            if (!event.data || event.data.trim() === "") return;
            
            try {
                const payload = JSON.parse(event.data);
                if (payload.event === 'connected') {
                    console.log("[Stream] Cosmic link established.");
                    return;
                }
                showCosmicActivity(payload);
            } catch (e) { 
                // Ignore parsing errors for heartbeats or malformed chunks
            }
        };

        source.onerror = () => {
            console.warn("[Stream] Connection interrupted. Reconnecting in 5s...");
            source.close();
            clearTimeout(reconnectTimeout);
            reconnectTimeout = setTimeout(connect, 5000); // Phase 4 Reconnection Logic
        };
    };

    connect();
}

function showCosmicActivity(payload) {
    const ticker = document.getElementById('cosmic-ticker');
    if (!ticker) return;

    const toast = document.createElement('div');
    toast.className = 'glass-panel ghost-border px-5 py-3 rounded-full shadow-2xl animate-fade-up flex items-center gap-3 backdrop-blur-xl';
    toast.style.background = 'rgba(27,27,31,0.85)';
    toast.style.borderColor = 'rgba(242,202,80,0.2)';

    let icon = 'pulse';
    let text = 'Celestial activity detected.';

    if (payload.event === 'like_engagement') {
        icon = 'favorite';
        text = `A seeker linked with a ${payload.data.type}.`;
    } else if (payload.event === 'synthesis_started') {
        icon = 'psychology';
        text = `Deep synthesis initiated (${payload.data.tier} tier).`;
    } else if (payload.event === 'synthesis_completed') {
        icon = 'check_circle';
        text = `Philosophical revelation crystallized.`;
    }

    toast.innerHTML = `
        <span class="material-symbols-outlined text-[16px] text-primary">${icon}</span>
        <span class="text-[11px] font-semibold text-on-surface uppercase tracking-wider">${text}</span>
    `;

    ticker.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

// index.js - Landing Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const user = localStorage.getItem('levi_user');
    const heroBtn = document.querySelector('a[href="auth.html"] .btn-gold');
    const chatHeroBtn = document.querySelector('a[href="chat.html"]');

    if (user) {
        // Update Primary Hero
        const startLink = document.querySelector('a[href="auth.html"]');
        if (startLink) {
            startLink.href = 'studio.html';
            const btn = startLink.querySelector('.btn-gold');
            if (btn) btn.textContent = 'Enter Studio →';
        }
        
        // Update Chat Hero
        if (chatHeroBtn) {
            chatHeroBtn.querySelector('span').textContent = 'Open Chat →';
        }
    }

    // Initialize Pulse Feed
    if (window.api && window.api.getFeed) {
        loadPulse();
    }
});

async function loadPulse() {
    const pulseGrid = document.getElementById('pulse-grid');
    if (!pulseGrid) return;
    
    try {
        const feed = await window.api.getFeed(1, 4);
        if (feed && feed.length > 0) {
            pulseGrid.innerHTML = '';
            feed.forEach(item => {
                const card = document.createElement('div');
                card.className = 'glass-card ghost-border h-48 rounded-2xl overflow-hidden group';
                card.innerHTML = `
                    <div class="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110" 
                         style="background-image: url('${item.image_b64 || item.url}')"></div>
                    <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
                    <div class="absolute bottom-4 left-4 right-4">
                        <p class="text-[10px] text-primary uppercase font-bold tracking-widest mb-0.5">${item.type || 'Inspiration'}</p>
                        <p class="text-[11px] text-zinc-300 font-medium line-clamp-2 italic">"${item.prompt}"</p>
                    </div>
                `;
                pulseGrid.appendChild(card);
            });
        }
    } catch(e) {
        console.warn("[LEVI] Pulse feed failed:", e);
    }
}

initCosmicStream();

window.addEventListener('scroll', () => {
    const nav = document.querySelector('nav');
    if (window.scrollY > 50) {
        nav.classList.add('py-4', 'shadow-2xl');
        nav.classList.remove('py-6');
    } else {
        nav.classList.add('py-6');
        nav.classList.remove('py-4', 'shadow-2xl');
    }
});

