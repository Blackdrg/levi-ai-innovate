import { chat, generateQuoteImage } from './api.js';

let sessionId = localStorage.getItem('levi_session') || 'user_' + Math.random().toString(36).substr(2, 9);
localStorage.setItem('levi_session', sessionId);

const chatBox = document.getElementById('messages');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');

let recognition = null;
let synth = window.speechSynthesis;
let isListening = false;

// UI Utils
const getUI = () => window.ui || {};

function addMessage(text, role, className = '') {
  const msg = document.createElement('div');
  msg.className = `message-bubble ${role === 'user' ? 'user-message' : 'bot-message'} ${className}`;
  
  const label = role === 'user' ? 'You' : 'LEVI AI';
  const labelClass = role === 'user' ? 'text-white/70' : 'text-emerald-400';

  msg.innerHTML = `
    <div class="text-[10px] font-bold uppercase tracking-widest ${labelClass} mb-2">${label}</div>
    <div class="text-md leading-relaxed">${text}</div>
    ${role === 'bot' ? `
    <div class="flex items-center gap-3 mt-4 pt-3 border-t border-white/5">
      <button onclick="window.shareQuote('${text.replace(/'/g, "\\'")}')" class="text-xs text-muted hover:text-white transition-colors flex items-center gap-1">
        📤 Share
      </button>
      <button onclick="window.generateVisual('${text.replace(/'/g, "\\'")}')" class="text-xs text-muted hover:text-violet-400 transition-colors flex items-center gap-1">
        🎨 Visual
      </button>
      <button onclick="window.speakText('${text.replace(/'/g, "\\'")}')" class="text-xs text-muted hover:text-emerald-400 transition-colors flex items-center gap-1">
        🔊 Listen
      </button>
      <button onclick="window.regenerateChat(this, '${text.replace(/'/g, "\\'")}')" class="text-xs text-muted hover:text-violet-400 transition-colors flex items-center gap-1">
        🔄 Regenerate
      </button>
      <button onclick="window.likeQuote(this, '${text.replace(/'/g, "\\'")}')" data-type="feed" class="text-xs text-muted hover:text-pink-400 transition-colors flex items-center gap-1 ml-auto">
        🤍 Like
      </button>
    </div>
    ` : ''}
  `;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msg;
}

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  
  recognition.onstart = () => {
    isListening = true;
    micBtn.innerHTML = '🛑';
    micBtn.classList.add('text-red-500', 'animate-pulse');
    const ui = getUI();
    if (ui.showToast) ui.showToast("Listening for your wisdom...");
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
    const ui = getUI();
    if (ui.showToast) ui.showToast("Heard: " + transcript);
    // Optionally auto-send
    // sendMessage();
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error", event.error);
    isListening = false;
    micBtn.innerHTML = '🎤';
    micBtn.classList.remove('text-red-500', 'animate-pulse');
    const ui = getUI();
    if (ui.showToast) ui.showToast("Speech recognition failed: " + event.error, "error");
  };

  recognition.onend = () => {
    isListening = false;
    micBtn.innerHTML = '🎤';
    micBtn.classList.remove('text-red-500', 'animate-pulse');
  };
}

micBtn.onclick = () => {
  if (!recognition) {
    const ui = getUI();
    if (ui.showToast) ui.showToast("Voice recognition not supported in this browser.", "error");
    return;
  }
  if (isListening) {
    recognition.stop();
  } else {
    // Set language based on current setting
    recognition.lang = localStorage.getItem('levi_lang') === 'hi' ? 'hi-IN' : 'en-US';
    recognition.start();
  }
};

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  addMessage(text, 'user');

  const ui = getUI();
  const typingId = ui.addTypingMessage ? ui.addTypingMessage() : null;

  try {
    const data = await chat(text, sessionId);
    if (typingId && ui.removeTypingMessage) ui.removeTypingMessage(typingId);
    addMessage(data.response, 'bot');
  } catch (err) {
    if (typingId && ui.removeTypingMessage) ui.removeTypingMessage(typingId);
    addMessage("I'm sorry, I'm having trouble connecting to my creative circuits right now.", 'bot');
    console.error(err);
  }
}

// Global Actions
window.shareQuote = (text) => {
  if (navigator.share) {
    navigator.share({ title: 'LEVI Wisdom', text }).catch(console.error);
  } else {
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
    window.open(twitterUrl, '_blank');
  }
};

window.speakText = (text) => {
  if (!synth) return;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1;
  synth.speak(utterance);
};

window.generateVisual = async (text) => {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black/90 backdrop-blur-xl flex items-center justify-center z-[100] animate-fade-in p-6';
  modal.innerHTML = `
    <div class="glass-card p-8 rounded-[2rem] max-w-lg w-full text-center relative">
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
    const data = await generateQuoteImage(text);
    const resultContainer = document.getElementById('visual-result');
    const loadingContainer = document.getElementById('visual-loading');
    const img = document.getElementById('generated-img');
    
    if (img && resultContainer && loadingContainer) {
        img.src = data.image_b64;
        loadingContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        
        // Attach ID to the like button in the modal if needed
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) saveBtn.dataset.id = data.id;
        
        // Add fade-in effect to the image
        img.classList.add('animate-fade-in');
    }
    
    document.getElementById('download-btn').onclick = () => {
      const link = document.createElement('a');
      link.href = document.getElementById('generated-img').src;
      link.download = 'levi-art.png';
      link.click();
    };

    window.updateArtStyle = (filter) => {
        document.getElementById('generated-img').style.filter = filter;
    };

    window.downloadRes = async (w, h) => {
        // Simple client-side resize using canvas
        const img = document.getElementById('generated-img');
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        
        // Fill background (if transparency)
        ctx.fillStyle = "#050B14";
        ctx.fillRect(0, 0, w, h);
        
        // Draw image (cover style)
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
  } catch (err) {
    modal.remove();
    alert("Failed to generate visual. Please try again.");
  }
};

// Event Listeners
sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});

// Mood Buttons in Chat
document.querySelectorAll('.mood-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const mood = btn.dataset.mood;
    input.value = `Give me some ${mood} wisdom`;
    sendMessage();
  });
});

// Speech Recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new Recognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  
  recognition.onresult = (event) => {
    input.value = event.results[0][0].transcript;
    micBtn.classList.remove('text-red-500', 'animate-pulse');
    isListening = false;
    sendMessage();
  };

  recognition.onerror = () => {
    micBtn.classList.remove('text-red-500', 'animate-pulse');
    isListening = false;
  };

  micBtn.addEventListener('click', () => {
    if (isListening) {
      recognition.stop();
      micBtn.classList.remove('text-red-500', 'animate-pulse');
    } else {
      recognition.start();
      micBtn.classList.add('text-red-500', 'animate-pulse');
    }
    isListening = !isListening;
  });
} else {
  micBtn.style.display = 'none';
}


