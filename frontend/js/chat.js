/**
 * LEVI-AI Chat Logic
 * Phase 6: Production Hardened & Synchronized
 */

// --- Global State ---
let currentMood = localStorage.getItem('levi_chat_mood') || "philosophical";
let messageCount = 0;
let lastBotMessage = "";
let sessionId = localStorage.getItem("levi_session_id") || `session_${Math.random().toString(36).substring(2, 11)}`;
localStorage.setItem("levi_session_id", sessionId);

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Auth Guard & Sync
    try {
        const user = await window.api.getMe();
        console.log("[LEVI] Session Active:", user.username);
        
        // 2. Load Real History
        await loadChatHistory();
        
        // 3. Load Memory/Facts
        await loadMemory();
        
        // 4. Initial Greeting if empty
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv && messagesDiv.children.length === 0) {
            displayWelcomeMessage();
        }
    } catch (e) {
        if (e.message === "UNAUTHORIZED") return; // Handled by api.js redirect
        console.error("[LEVI] Init failed", e);
    }

    // 5. Setup UI
    const input = document.getElementById("chat-input");
    if (input) {
        input.focus();
        // Restore mood active state
        const activeBtn = Array.from(document.querySelectorAll('.mood-chip')).find(b => b.textContent.toLowerCase() === currentMood);
        if (activeBtn) setMood(activeBtn, currentMood);
    }
});

async function loadChatHistory() {
    try {
        const res = await window.api.apiFetch("/chat/history?limit=20");
        const history = res.history || [];
        
        const messagesDiv = document.getElementById("messages");
        if (!messagesDiv) return;
        messagesDiv.innerHTML = ""; // Clear loader/old state
        
        history.forEach(msg => {
            appendMessage(msg.role, msg.content, null, false);
        });
        
        messageCount = history.length;
    } catch (e) {
        console.warn("[LEVI] Could not load history", e);
    }
}

async function loadMemory() {
    try {
        const res = await window.api.getMemory();
        if (res.facts && res.facts.length > 0) {
            console.log("[LEVI] Memory Hydrated:", res.facts.length, "facts");
            // Optional: Show a "Personalized" badge in the UI
            const statusLabel = document.getElementById("status-label");
            if (statusLabel) statusLabel.innerText = "Synchronized";
        }
    } catch (e) {
        console.warn("[LEVI] Memory retrieval failed", e);
    }
}

function displayWelcomeMessage() {
    appendMessage('bot', "Hello, I am **LEVI** — your philosophical AI companion. Our connection is now live. What shall we explore today?", null, true);
}

// --- UI Actions ---

function setMood(element, mood) {
    document.querySelectorAll('.mood-chip').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    currentMood = mood;
    localStorage.setItem('levi_chat_mood', mood);
    
    const sessionInfo = document.getElementById("session-info");
    if (sessionInfo) {
        const user = JSON.parse(localStorage.getItem('levi_user') || '{}');
        const name = user.username || "Seeker";
        sessionInfo.innerText = `${name} · ${mood.charAt(0).toUpperCase() + mood.slice(1)} Mode`;
    }
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
    if (confirm("Are you sure you want to clear this cosmic resonance?")) {
        const messagesDiv = document.getElementById("messages");
        if (messagesDiv) messagesDiv.innerHTML = "";
        displayWelcomeMessage();
        messageCount = 0;
        // In production, we might call a backend endpoint to clear history, 
        // but here we just clear the local UI view.
    }
}

function appendMessage(role, text, id = null, animate = true) {
    const messagesDiv = document.getElementById("messages");
    if (!messagesDiv) return;
    
    const div = document.createElement("div");
    div.className = `message-wrap flex ${role === 'user' ? 'justify-end' : 'justify-start'} ${animate ? 'animate-in' : ''}`;
    
    let renderedText = text;
    if (typeof marked !== 'undefined') {
        renderedText = marked.parse(text);
    }

    const innerDiv = document.createElement("div");
    if (role === 'user') {
        innerDiv.className = "msg-user p-4 text-sm text-on-surface leading-relaxed shadow-sm";
    } else {
        innerDiv.className = "msg-bot p-4 text-sm text-on-surface-variant flex flex-col gap-2 shadow-sm";
    }
    
    innerDiv.innerHTML = renderedText;
    
    // Add Metadata/Controls for Bot messages
    if (role === 'bot' || role === 'assistant') {
        const msgId = id || `msg_${Date.now()}`;
        const controls = document.createElement("div");
        controls.className = "flex items-center gap-3 mt-2 pt-2 border-t border-white/5";
        controls.innerHTML = `
            <button onclick="submitFeedback('${msgId}', 1, this)" class="text-zinc-500 hover:text-emerald-400 transition-colors" title="Accurate"><span class="material-symbols-outlined icon-sm">thumb_up</span></button>
            <button onclick="submitFeedback('${msgId}', 0, this)" class="text-zinc-500 hover:text-red-400 transition-colors" title="Inaccurate"><span class="material-symbols-outlined icon-sm">thumb_down</span></button>
        `;
        innerDiv.appendChild(controls);
        lastBotMessage = text;
    }

    div.appendChild(innerDiv);
    messagesDiv.appendChild(div);
    messagesDiv.scrollTo({ top: messagesDiv.scrollHeight, behavior: animate ? 'smooth' : 'auto' });
}

async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    appendMessage('user', text);
    input.value = "";
    input.style.height = 'auto';

    const sendIcon = document.getElementById("send-icon");
    const spinner = document.getElementById("send-loading");
    if(sendIcon) sendIcon.classList.add("hidden");
    if(spinner) spinner.classList.remove("hidden");

    // Prepare Bot Message Placeholder (Dynamic Streaming)
    const messagesDiv = document.getElementById("messages");
    const botWrap = document.createElement("div");
    botWrap.className = "message-wrap flex justify-start animate-in";
    
    const botDiv = document.createElement("div");
    botDiv.className = "msg-bot p-4 text-sm text-on-surface-variant flex flex-col gap-2 shadow-sm";
    
    const textSpan = document.createElement("div");
    textSpan.className = "leading-relaxed whitespace-pre-wrap";
    botDiv.appendChild(textSpan);
    botWrap.appendChild(botDiv);
    messagesDiv.appendChild(botWrap);
    
    let botFullText = "";
    let metadataCaptured = null;

    try {
        await window.api.chatStream(
            text, 
            sessionId, 
            (chunk) => {
                botFullText += chunk;
                textSpan.innerHTML = typeof marked !== 'undefined' ? marked.parse(botFullText) : botFullText;
                messagesDiv.scrollTo({ top: messagesDiv.scrollHeight, behavior: 'auto' });
            },
            (meta) => {
                metadataCaptured = meta;
                
                // Real-time Intelligence Status rendering
                if (meta.status_update) {
                    let statusDiv = botDiv.querySelector('.levi-status-indicator');
                    if (!statusDiv) {
                        statusDiv = document.createElement('div');
                        statusDiv.className = 'levi-status-indicator text-[9px] text-primary/60 font-mono italic mb-2 animate-pulse';
                        botDiv.prepend(statusDiv);
                    }
                    statusDiv.innerText = `● ${meta.status_update}`;
                }
            },
            currentMood
        );

        messageCount++;
        lastBotMessage = botFullText;

        // Post-Stream: Add controls & engine badges
        const controls = document.createElement("div");
        controls.className = "flex items-center gap-3 mt-2 pt-2 border-t border-white/5 w-full";
        
        const msgId = metadataCaptured?.request_id || `msg_${Date.now()}`;
        const routeBadge = _buildRouteBadge(metadataCaptured);
        
        controls.innerHTML = `
            <button onclick="submitFeedback('${msgId}', 1, this)" class="text-zinc-500 hover:text-emerald-400 transition-colors"><span class="material-symbols-outlined icon-sm">thumb_up</span></button>
            <button onclick="submitFeedback('${msgId}', 0, this)" class="text-zinc-500 hover:text-red-400 transition-colors"><span class="material-symbols-outlined icon-sm">thumb_down</span></button>
            <div class="ml-auto">${routeBadge}</div>
        `;
        botDiv.appendChild(controls);

        // Auto-Save fact if high confidence (Logic handled by backend, but we could trigger it here if needed)

    } catch (err) {
        console.error("Chat error:", err);
        textSpan.innerText = "The connection to the cosmic brain was interrupted. Please try again.";
        botDiv.classList.add("border-red-500/30", "bg-red-500/5");
    } finally {
        if(sendIcon) sendIcon.classList.remove("hidden");
        if(spinner) spinner.classList.add("hidden");
        
        // Sync user credits
        if (window.syncUser) window.syncUser();
    }
}

async function submitFeedback(msgId, score, btn) {
    const parent = btn.parentElement;
    parent.innerHTML = `<span class="text-[9px] text-emerald-400/80 uppercase tracking-widest flex items-center gap-1"><span class="material-symbols-outlined icon-sm">check_circle</span> Learned</span>`;
    
    try {
        await window.api.apiFetch("/learning/feedback", {
            method: "POST",
            body: { 
                session_id: sessionId,
                rating: score ? 5 : 1, // mapping 1/0 to 5/1 stars
                user_message: "...", // ideally we'd store these
                bot_response: "...",
                mood: currentMood
            }
        });
    } catch (e) {
        console.error("Feedback failed", e);
    }
}

function _buildRouteBadge(meta) {
    if (!meta?.route) return '';
    const route = meta.route.toLowerCase();
    const configs = {
        cache: { emoji: '⚡', label: 'Cached', color: 'text-emerald-400/80' },
        local: { emoji: '🟢', label: 'Local', color: 'text-emerald-400/60' },
        tool:  { emoji: '🟡', label: 'Agent', color: 'text-amber-400/60' },
        api:   { emoji: '🔴', label: 'Brain', color: 'text-rose-400/60' },
    };
    const cfg = configs[route] || { emoji: '⚪', label: route, color: 'text-zinc-500' };
    return `<span class="text-[9px] ${cfg.color} font-mono tracking-widest uppercase select-none cursor-default">${cfg.emoji} ${cfg.label}</span>`;
}

// --- Speech Helpers ---
let currentUtterance = null;
function speakLast() {
    if (!lastBotMessage || window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        return;
    }
    currentUtterance = new SpeechSynthesisUtterance(lastBotMessage.replace(/[*#]/g, ''));
    currentUtterance.rate = 0.95;
    window.speechSynthesis.speak(currentUtterance);
}

// --- Voice Input ---
let recognition;
function startVoice() {
    const btn = document.getElementById("voice-btn");
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    
    if (!recognition) {
        recognition = new SpeechRecognition();
        recognition.onstart = () => btn.classList.add("text-primary", "animate-pulse");
        recognition.onresult = (e) => {
            const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
            document.getElementById("chat-input").value = transcript;
        };
        recognition.onend = () => btn.classList.remove("text-primary", "animate-pulse");
    }
    
    try { recognition.start(); } catch(e) { recognition.stop(); }
}

// Expose functions to window
window.setMood = setMood;
window.handleKey = handleKey;
window.autoResize = autoResize;
window.clearChat = clearChat;
window.sendMessage = sendMessage;
window.submitFeedback = submitFeedback;
window.speakLast = speakLast;
window.startVoice = startVoice;
