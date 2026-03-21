import { searchQuotes } from './api.js';

const searchInput = document.getElementById('search-input');
const container = document.getElementById('quotes-list');
const moodButtons = document.querySelectorAll('.mood-btn');

let currentMood = '';

function shareQuote(text) {
  if (window.ui && window.ui.shareContent) {
    window.ui.shareContent("LEVI Quote", text, window.location.href);
    return;
  }
  const encoded = encodeURIComponent(text);
  const shares = [
    `https://twitter.com/intent/tweet?text=${encoded}`,
    `https://wa.me/?text=${encoded}`
  ];
  if (navigator.share) {
    navigator.share({title: 'LEVI Quote', text}).catch(() => window.open(shares[0]));
  } else {
    window.open(shares[0]);
  }
}

// Make globally available for onclick
window.shareQuote = shareQuote;

async function search() {
  const text = searchInput.value;
  try {
    const results = await searchQuotes(text, { mood: currentMood });
    displayQuotes(results);
  } catch (err) {
    container.innerHTML = '<p class="text-center opacity-70">Backend not ready. Make sure Docker is running!</p>';
  }
}

function displayQuotes(quotes) {
  if (!quotes || quotes.length === 0) {
    container.innerHTML = '<p class="col-span-full text-center py-20 text-muted italic">No wisdom found for this search. Try another path.</p>';
    return;
  }
  container.innerHTML = quotes.map(q => `
    <div class="quote-card group glass p-8 rounded-[2rem] border border-white/5 hover:border-violet-500/30 transition-all duration-500 animate-fade-in-up" onclick="navigator.clipboard.writeText('${q.quote.replace(/'/g, "\\'")}')">
      <div class="mb-6">
        <span class="text-[10px] font-bold tracking-[0.2em] uppercase text-violet-400/60">${q.topic || 'Wisdom'}</span>
      </div>
      <p class="text-xl font-display italic mb-6 leading-relaxed">"${q.quote}"</p>
      <div class="flex items-center justify-between mt-auto">
        <p class="text-sm font-bold tracking-widest uppercase text-slate-400">${q.author || 'Anonymous'}</p>
        <div class="flex gap-2">
           <button onclick="window.shareQuote('${q.quote.replace(/'/g, "\\'")}'); event.stopPropagation();" class="p-2 rounded-xl bg-white/5 hover:bg-violet-500/20 text-white transition-all">
             <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
             </svg>
           </button>
        </div>
      </div>
    </div>
  `).join('');
}

moodButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    moodButtons.forEach(b => b.classList.remove('ring-2', 'ring-violet-500', 'bg-violet-500/10'));
    if (currentMood === btn.dataset.mood) {
      currentMood = '';
    } else {
      currentMood = btn.dataset.mood;
      btn.classList.add('ring-2', 'ring-violet-500', 'bg-violet-500/10');
    }
    search();
  });
});

searchInput.addEventListener('input', () => {
    // Debounce search
    if (window._searchTimeout) clearTimeout(window._searchTimeout);
    window._searchTimeout = setTimeout(search, 300);
});

search();

