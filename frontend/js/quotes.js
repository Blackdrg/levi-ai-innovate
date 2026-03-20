import { searchQuotes } from './api.js';

const searchInput = document.getElementById('search-input');
const container = document.getElementById('quotes-list');

function shareQuote(text) {
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
  if (!text) return;
  try {
    const results = await searchQuotes(text);
    displayQuotes(results);
  } catch (err) {
    container.innerHTML = '<p class="text-center opacity-70">Backend not ready. Make sure Docker is running!</p>';
  }
}

function displayQuotes(quotes) {
  container.innerHTML = quotes.map(q => `
    <div class="quote-card group glass p-6 rounded-2xl cursor-pointer hover:shadow-2xl transition-all animate-fade-in-up" onclick="navigator.clipboard.writeText('${q.quote.replace(/'/g, "\\'")}')">
      <p class="text-lg italic mb-2">"${q.quote}"</p>
      <p class="text-sm opacity-90 font-semibold mb-2">${q.author || 'Anonymous'}</p>
      <div class="text-xs opacity-75 mb-4">${(q.similarity * 100).toFixed(1)}% match</div>
      <div class="quote-actions flex gap-2 flex-wrap mt-auto">
        <button onclick="navigator.clipboard.writeText('${q.quote.replace(/'/g, "\\'")}'); event.stopPropagation();" class="px-3 py-1.5 rounded-full bg-blue-500/80 hover:bg-blue-400 text-white text-xs shadow-md transition-all">📋 Copy</button>
        <button onclick="window.shareQuote('${q.quote.replace(/'/g, "\\'")}'); event.stopPropagation();" class="px-3 py-1.5 rounded-full bg-indigo-500/80 hover:bg-indigo-400 text-white text-xs shadow-md transition-all">📤 Share</button>
      </div>
    </div>
  `).join('');
}

searchInput.addEventListener('input', search);

search();

