// chat.js
document.addEventListener("DOMContentLoaded", () => {
    // Load marked.js for markdown rendering
    if (typeof marked === 'undefined') {
        const script = document.createElement('script');
        script.src = "https://cdn.jsdelivr.net/npm/marked/marked.min.js";
        document.head.appendChild(script);
    }
});

let currentMood = "inspiring";
let messageCount = 0;
let chatHistory = [];
let lastBotMessage = "";

function setMood(element, mood) {
    document.querySelectorAll('.mood-chip').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    currentMood = mood;
    document.getElementById("session-info").innerText = `Anonymous · ${mood.charAt(0).toUpperCase() + mood.slice(1)} Mode`;
}

function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

function clearChat() {
    const messagesDiv = document.getElementById("messages");
    if (messagesDiv) {
        messagesDiv.innerHTML = `
            <div class="msg-bot p-4 fade-in">
              <p class="text-sm text-on-surface-variant font-light leading-relaxed">Chat history cleared. What shall we explore next?</p>
            </div>`;
    }
    chatHistory = [];
    messageCount = 0;
}

function showToast(text) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.innerText = text;
    toast.className = "bg-primary text-on-primary px-4 py-2 rounded-full text-sm font-semibold show";
    setTimeout(() => { toast.classList.remove("show"); }, 3000);
}

function appendMessage(role, text, id = null) {
    const messagesDiv = document.getElementById("messages");
    if (!messagesDiv) return;
    
    const div = document.createElement("div");
    
    // Parse markdown if marked is loaded
    let renderedText = text;
    if (typeof marked !== 'undefined') {
        renderedText = marked.parse(text);
    }

    if (role === 'user') {
        div.className = "msg-user p-4 fade-in text-sm text-on-surface";
        div.innerHTML = renderedText;
    } else {
        div.className = "msg-bot p-4 fade-in text-sm text-on-surface-variant flex flex-col gap-2";
        let content = `<div class="leading-relaxed whitespace-pre-wrap">${renderedText}</div>`;
        
        // Add thumbs up/down for learning pipeline
        const msgId = id || `msg_${Date.now()}`;
        content += `
        <div class="flex items-center gap-2 mt-2 pt-2 border-t border-white/10">
            <button onclick="submitFeedback('${msgId}', 1.0, this)" class="text-zinc-500 hover:text-emerald-400 transition-colors" title="Good response"><span class="material-symbols-outlined icon-sm">thumb_up</span></button>
            <button onclick="submitFeedback('${msgId}', 0.0, this)" class="text-zinc-500 hover:text-red-400 transition-colors" title="Bad response"><span class="material-symbols-outlined icon-sm">thumb_down</span></button>
        </div>`;
        
        // Every 3rd message, suggest visual art piece
        if (messageCount > 0 && messageCount % 3 === 0) {
            const encQuote = encodeURIComponent(text.substring(0, 200) + "...");
            content += `
            <div class="mt-3 bg-surface-container rounded p-3 border border-primary/20 flex flex-col items-center text-center">
                <span class="material-symbols-outlined gold-text mb-1">palette</span>
                <p class="text-xs text-on-surface mb-2 font-medium">Turn this thought into a visual art piece?</p>
                <a href="studio.html?quote=${encQuote}&mood=${currentMood}" class="btn-gold text-[10px] uppercase font-bold px-4 py-1.5 rounded-full inline-block">Create Art</a>
            </div>`;
        }
        
        div.innerHTML = content;
        lastBotMessage = text;
    }
    
    messagesDiv.appendChild(div);
    messagesDiv.scrollTo({ top: messagesDiv.scrollHeight, behavior: 'smooth' });
}

async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    appendMessage('user', text);
    input.value = "";
    input.style.height = 'auto';
    chatHistory.push({ user: text });

    const sendIcon = document.getElementById("send-icon");
    const spinner = document.getElementById("send-loading");
    if(sendIcon) sendIcon.classList.add("hidden");
    if(spinner) spinner.classList.remove("hidden");

    let sessionId = sessionStorage.getItem("chat_session_id");
    if (!sessionId) {
        sessionId = "session_" + Math.random().toString(36).substring(2, 15);
        sessionStorage.setItem("chat_session_id", sessionId);
    }

    if (window.ui && window.ui.showLoader) window.ui.showLoader();
    try {
        await window.waitForToken();
        const data = await window.api.chat(text, sessionId);
        
        messageCount++;
        
        const msgId = data.id || `msg_${Date.now()}`; 
        const finalReply = data.response || data.reply || "";
        
        if (!finalReply) {
            if (typeof showToast === 'function') showToast("Chat failed - empty response", "error");
        }
        
        appendMessage('bot', finalReply || "A profound silence.", msgId);
        chatHistory[chatHistory.length - 1].bot = finalReply;
        
    } catch (err) {
        console.error("Chat error:", err);
        if (typeof showToast === 'function') showToast("Network error", "error");
        appendMessage('bot', "Connection to the cosmic ether was lost. (Error connecting to server)");
    } finally {
        if(sendIcon) sendIcon.classList.remove("hidden");
        if(spinner) spinner.classList.add("hidden");
        if (window.ui && window.ui.hideLoader) window.ui.hideLoader();
    }
}

async function submitFeedback(msgId, score, btn) {
    // visual feedback
    const parent = btn.parentElement;
    parent.innerHTML = `<span class="text-[10px] text-emerald-400 uppercase tracking-widest"><span class="material-symbols-outlined icon-sm align-middle mr-1">check</span>Feedback saved</span>`;
    
    try {
        await window.waitForToken();
        await fetch(`${window.API_BASE}/analytics/feedback`, {
            method: "POST",
            body: JSON.stringify({ message_id: msgId, score: score })
        });
    } catch (e) {
        console.error("Feedback failed", e);
    }
}

// Global speech synthesis tracking
let currentUtterance = null;
let voicesLoaded = false;
let preferredVoiceName = localStorage.getItem("levi_preferred_voice") || null;

window.speechSynthesis.onvoiceschanged = () => { voicesLoaded = true; };

function speakLast() {
    if (!lastBotMessage) {
        showToast("Nothing to speak yet.");
        return;
    }
    
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        return;
    }

    const ttsBtn = document.getElementById("tts-btn");
    
    currentUtterance = new SpeechSynthesisUtterance(lastBotMessage.replace(/[*#]/g, ''));
    
    // Smart voice selection
    const voices = window.speechSynthesis.getVoices();
    let selectedVoice = null;
    
    if (preferredVoiceName) {
        selectedVoice = voices.find(v => v.name === preferredVoiceName);
    }
    
    if (!selectedVoice) {
        // Try to find a good authoritative/calm voice
        const preferred = ['Google UK English Male', 'Daniel', 'Alex', 'Samantha'];
        for (let name of preferred) {
            selectedVoice = voices.find(v => v.name.includes(name));
            if (selectedVoice) break;
        }
    }
    
    if (selectedVoice) currentUtterance.voice = selectedVoice;
    currentUtterance.rate = 0.9; // Slightly slower, calmer
    currentUtterance.pitch = 0.95; 

    currentUtterance.onstart = () => {
        if (ttsBtn) ttsBtn.classList.add("text-primary");
    };
    currentUtterance.onend = () => {
        if (ttsBtn) ttsBtn.classList.remove("text-primary");
    };
    currentUtterance.onerror = () => {
        if (ttsBtn) ttsBtn.classList.remove("text-primary");
    };

    window.speechSynthesis.speak(currentUtterance);
}

// Provide a way to change voice from console or later settings
window.setPreferredVoice = function(name) {
    preferredVoiceName = name;
    localStorage.setItem("levi_preferred_voice", name);
    showToast(`Voice set to: ${name}`);
};

// Start Voice Input (Web Speech API)
let recognition;
function startVoice() {
    const btn = document.getElementById("voice-btn");
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showToast("Voice input not supported in this browser.");
        return;
    }
    
    if (!recognition) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        
        recognition.onstart = () => {
            if(btn) btn.classList.add("text-primary", "animate-pulse");
        };
        
        recognition.onresult = (e) => {
            let finalOutput = '';
            for (let i = e.resultIndex; i < e.results.length; ++i) {
                if (e.results[i].isFinal) {
                    finalOutput += e.results[i][0].transcript;
                }
            }
            if (finalOutput) {
                const input = document.getElementById("chat-input");
                input.value += (input.value ? " " : "") + finalOutput;
                autoResize(input);
            }
        };
        
        recognition.onend = () => {
            if(btn) btn.classList.remove("text-primary", "animate-pulse");
        };
        
        recognition.onerror = () => {
            if(btn) btn.classList.remove("text-primary", "animate-pulse");
            showToast("Microphone error.");
        };
    }
    
    try {
        recognition.start();
    } catch(e) {
        recognition.stop();
    }
}

// Expose to window for inline HTML attachments
window.setMood = setMood;
window.handleKey = handleKey;
window.autoResize = autoResize;
window.clearChat = clearChat;
window.sendMessage = sendMessage;
window.submitFeedback = submitFeedback;
window.speakLast = speakLast;
window.startVoice = startVoice;
