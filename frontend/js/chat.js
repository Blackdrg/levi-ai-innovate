// Centralized API import
import { chat } from './api.js';

let sessionId = localStorage.getItem('levi_session') || 'user_' + Math.random().toString(36).substr(2, 9);
localStorage.setItem('levi_session', sessionId);

const chatBox = document.getElementById('messages');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const voiceBtn = document.getElementById('voice-btn');

let recognition = null;
let synth = window.speechSynthesis;
let isListening = false;

// UI utils from global
const { selectMood, addTypingMessage, removeTypingMessage } = window.ui || {};
const currentMoods = (window.ui && window.ui.currentMoods) || [];

function addMessage(text, role, className = '') {
  const msg = document.createElement('div');
  msg.className = `p-4 rounded-2xl message-bubble ${role === 'user' ? 'bg-indigo-600/50 self-end ml-auto' : 'bg-slate-800/80 mr-auto'} ${className}`;
  msg.innerHTML = `
    <div class="text-sm font-semibold opacity-70 mb-1">${role.toUpperCase()}</div>
    <div>${text}</div>
    <div class="flex gap-2 mt-2 opacity-70">
      <button onclick="window.shareQuote('${text.replace(/'/g, "\\'")}')" class="p-1 text-xs rounded bg-blue-500/50 hover:bg-blue-400/80">📤 Share</button>
      <button onclick="window.speakText('${text.replace(/'/g, "\\'")}')" class="p-1 text-xs rounded bg-green-500/50 hover:bg-green-400/80">🔊</button>
    </div>
  `;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function shareQuote(text) {
  if (window.ui && window.ui.shareContent) {
    window.ui.shareContent("LEVI Wisdom", text, window.location.href);
    return;
  }
  const shares = [
    `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`,
    `https://wa.me/?text=${encodeURIComponent(text)}`
  ];
  if (navigator.share) {
    navigator.share({title: 'LEVI Quote', text, url: window.location.href}).catch(() => window.open(shares[0]));
  } else {
    window.open(shares[0]);
  }
}

function speakText(text) {
  if (!synth) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  synth.speak(utterance);
}

// Make globally available for onclick
window.shareQuote = shareQuote;
window.speakText = speakText;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new Recognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    input.value = event.results[0][0].transcript;
    isListening = false;
    micBtn.classList.remove('bg-red-500', 'animate-pulse');
  };

  recognition.onerror = () => {
    isListening = false;
    micBtn.classList.remove('bg-red-500', 'animate-pulse');
  };
} else {
  micBtn.style.display = 'none';
}

micBtn.addEventListener('click', () => {
  if (isListening) {
    recognition.stop();
  } else {
    recognition.start();
  }
  isListening = !isListening;
  micBtn.classList.toggle('bg-red-500', isListening);
  micBtn.classList.toggle('animate-pulse', isListening);
});

if (voiceBtn) {
  voiceBtn.addEventListener('click', () => {
    if (synth && synth.speaking) synth.cancel();
  });
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});

document.querySelectorAll('.mood-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    if (selectMood) selectMood(btn.dataset.mood, btn);
  });
});

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;

  addMessage(message, "user");
  input.value = '';

  const typingId = addTypingMessage ? addTypingMessage() : null;

  const mood = currentMoods[0] || '';
  try {
    const response = await chat(message, sessionId);
    if (removeTypingMessage) removeTypingMessage(typingId);
    addMessage(response.response || "No response", "bot");
  } catch (err) {
    if (removeTypingMessage) removeTypingMessage(typingId);
    addMessage('Sorry, backend not running. Run docker-compose up!', "bot");
  }
}

