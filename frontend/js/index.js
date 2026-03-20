import { getDailyQuote, getAnalytics, getHealth, chat, getFeed, likeItem, searchQuotes } from './api.js';

// 1. System Health Status
async function checkStatus() {
    const statusIndicator = document.getElementById('status-indicator');
    const offlineBanner = document.getElementById('offline-banner');
    try {
        const data = await getHealth();
        if (data && (data.status === 'ok' || data.status === 'healthy')) {
            statusIndicator.classList.remove('bg-red-500');
            statusIndicator.classList.add('bg-emerald-500');
            statusIndicator.title = "System Online";
            offlineBanner.style.display = 'none';
        } else {
            statusIndicator.classList.add('bg-red-500');
            statusIndicator.classList.remove('bg-emerald-500');
            statusIndicator.title = "System Offline";
            offlineBanner.style.display = 'block';
        }
    } catch (err) {
        statusIndicator.classList.add('bg-red-500');
        statusIndicator.classList.remove('bg-emerald-500');
        offlineBanner.style.display = 'block';
    }
}
checkStatus();
setInterval(checkStatus, 30000); // Check every 30s

// 2. Stats Animation
async function loadStats() {
    try {
        const data = await getAnalytics();
        if (data) {
            animateValue("stat-quotes", 0, data.total_quotes || 1240, 2000);
            animateValue("stat-artists", 0, data.total_users || 542, 2000);
            animateValue("stat-uptime", 0, 99, 2000, "%");
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
        const data = await getDailyQuote();
        if (data) {
            quoteEl.textContent = `"${data.text}"`;
            authorEl.textContent = data.author || "LEVI AI";
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
        const response = await chat(msg, "demo-session");
        typingIndicator.classList.add('opacity-0');
        appendMessage(response.response, 'bot');
    } catch (err) {
        typingIndicator.classList.add('opacity-0');
        appendMessage("The connection to the cosmic archive was interrupted. Please try again.", 'bot');
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
searchInput.oninput = () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        const query = searchInput.value.trim();
        if (query.length > 3) {
            console.log(`Searching for: ${query}`);
            // Optionally trigger search or show preview
        }
    }, 500);
};

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
    try {
        const items = await getFeed(2);
        if (items && items.length > 0) {
            const cards = galleryGrid.querySelectorAll('.group');
            items.forEach((item, i) => {
                if (cards[i]) {
                    const img = cards[i].querySelector('img');
                    const quote = cards[i].querySelector('.font-display');
                    const author = cards[i].querySelector('.text-gold');
                    const likeBtn = cards[i].querySelector('button');

                    img.src = item.image_b64;
                    quote.textContent = `"${item.text}"`;
                    author.textContent = item.author || "Anonymous";

                    likeBtn.onclick = async () => {
                        try {
                            await likeItem('feed', item.id);
                            likeBtn.classList.add('text-pink-500');
                        } catch (err) { console.error(err); }
                    };
                }
            });
        }
    } catch (err) {
        console.warn("Gallery feed failed");
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

