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

// Brain Routing & Memory State
let sessionMessages = [];
let appMode = "chat";
let uploadedDoc = null;
let cy = null; // Cytoscape instance

// --- LocalStorage Caching ---
function saveToCache() {
    localStorage.setItem(`levi_history_${sessionId}`, JSON.stringify(sessionMessages));
}
function loadFromCache() {
    try {
        const cached = localStorage.getItem(`levi_history_${sessionId}`);
        if (cached) {
            const data = JSON.parse(cached);
            if (Array.isArray(data) && data.length > 0) return data;
        }
    } catch (e) { }
    return null;
}

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
        // Restore pending input
        const pending = localStorage.getItem(`levi_pending_input_${sessionId}`);
        if (pending) {
            input.value = pending;
            autoResize(input);
        }
        input.addEventListener('input', (e) => {
            localStorage.setItem(`levi_pending_input_${sessionId}`, e.target.value);
        });

        input.focus();
        // Restore mood active state
        const activeBtn = Array.from(document.querySelectorAll('.mood-chip')).find(b => b.textContent.toLowerCase() === currentMood);
        if (activeBtn) setMood(activeBtn, currentMood);
    }
});

async function loadChatHistory() {
    // 1. Instantly load from cache
    const cached = loadFromCache();
    if (cached) {
        const messagesDiv = document.getElementById("messages");
        if (messagesDiv) {
            messagesDiv.innerHTML = "";
            sessionMessages = [];
            cached.forEach(msg => {
                appendMessage(msg.role, msg.content, null, false);
                sessionMessages.push(msg);
            });
            messageCount = cached.length;
        }
    }

    try {
        const res = await window.api.apiFetch("/chat/history?limit=20");
        const history = res.history || [];

        // 2. Reconcile with backend if needed
        if (history.length > 0 && (!cached || history.length !== cached.length)) {
            const messagesDiv = document.getElementById("messages");
            if (!messagesDiv) return;
            messagesDiv.innerHTML = ""; // Clear loader/old state
            sessionMessages = []; // Reset memory

            history.forEach(msg => {
                appendMessage(msg.role, msg.content, null, false);
                sessionMessages.push({ role: msg.role, content: msg.content });
            });

            messageCount = history.length;
            saveToCache();
        }
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
        sessionMessages = [];
        saveToCache();
        localStorage.removeItem(`levi_pending_input_${sessionId}`);
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
    if (sendIcon) sendIcon.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

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

    sessionMessages.push({ role: "user", content: text });
    saveToCache();
    localStorage.removeItem(`levi_pending_input_${sessionId}`);

    sessionMessages.push({ role: "user", content: text });
    saveToCache();
    localStorage.removeItem(`levi_pending_input_${sessionId}`);

    try {
        await LeviAPI.postStream('/api/v1/chat/stream', {
            message: text,
            session_id: sessionId,
            mood: currentMood,
            history: sessionMessages
        }, (event) => {
            // Handle different event types from the unified stream
            if (event.type === 'token') {
                botFullText += event.data;
                window.requestAnimationFrame(() => {
                    const parsed = typeof marked !== 'undefined' ? marked.parse(botFullText) : botFullText;
                    textSpan.innerHTML = parsed + '<span class="streaming-cursor"></span>';
                    messagesDiv.scrollTo({ top: messagesDiv.scrollHeight, behavior: 'auto' });
                });
            }

            if (event.type === 'audit') {
                let badgeContainer = botDiv.querySelector('.audit-badge-container');
                if (!badgeContainer) {
                    badgeContainer = document.createElement('div');
                    badgeContainer.className = 'audit-badge-container absolute -top-2 -right-2';
                    botDiv.style.position = 'relative';
                    botDiv.appendChild(badgeContainer);
                }
                badgeContainer.innerHTML = LeviUI.renderAuditBadge(event.status);
            }

            if (event.type === 'metadata') {
                console.log("[LEVI] Mission Pulse:", event.data.request_id);
                if (event.data.request_id) metadataCaptured = { ...metadataCaptured, ...event.data };
            }

            if (event.type === 'activity') {
                let statusDiv = botDiv.querySelector('.levi-status-indicator');
                if (!statusDiv) {
                    statusDiv = document.createElement('div');
                    statusDiv.className = 'levi-status-indicator text-[9px] text-neural/60 font-mono italic mb-2 animate-pulse';
                    botDiv.prepend(statusDiv);
                }
                statusDiv.innerText = `● ${event.data}`;
            }

            if (event.type === 'graph') {
                const panel = document.getElementById("mission-graph-panel");
                if (panel) {
                    panel.classList.remove("hidden");
                    _renderMissionGraph(event.data);
                }
            }
        });

        messageCount++;
        lastBotMessage = botFullText;
        textSpan.innerHTML = typeof marked !== 'undefined' ? marked.parse(botFullText) : botFullText; // Strip cursor

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

        // Search Mode UI: Render Sources if backend provided them
        if ((appMode === 'search' || (metadataCaptured && metadataCaptured.route === 'search')) && metadataCaptured && metadataCaptured.sources) {
            const sourcesDiv = document.createElement("div");
            sourcesDiv.className = "mt-3 pt-3 border-t border-white/5 flex flex-wrap gap-2";
            metadataCaptured.sources.forEach(src => {
                const link = document.createElement("a");
                link.href = src.link || "#";
                link.target = "_blank";
                link.className = "text-[10px] bg-white/5 hover:bg-white/10 px-2 py-1 rounded border border-white/10 text-primary transition-colors flex items-center gap-1";
                link.innerHTML = `<span class="material-symbols-outlined" style="font-size:10px">link</span>${src.title || 'Source'}`;
                sourcesDiv.appendChild(link);
            });
            botDiv.appendChild(sourcesDiv);
        }

        // Add to memory
        sessionMessages.push({ role: "assistant", content: botFullText });
        saveToCache();

        // Auto-Save fact if high confidence (Logic handled by backend, but we could trigger it here if needed)

    } catch (err) {
        console.error("Chat error:", err);
        textSpan.innerHTML = "The connection to the cosmic brain was interrupted. Please try again.";
        botDiv.classList.add("border-red-500/30", "bg-red-500/5");
    } finally {
        if (sendIcon) sendIcon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");

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
        tool: { emoji: '🟡', label: 'Agent', color: 'text-amber-400/60' },
        api: { emoji: '🔴', label: 'Brain', color: 'text-rose-400/60' },
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

    try { recognition.start(); } catch (e) { recognition.stop(); }
}

// --- Brain Routing & Modes ---
function switchMode(newMode) {
    const modes = {
        'chat': { icon: 'chat', label: 'Chat Mode', color: 'text-zinc-400', placeholder: 'Ask about life, stoicism, the cosmos…' },
        'search': { icon: 'travel_explore', label: 'Search Mode', color: 'text-blue-400', placeholder: 'Ask anything to search the web…' },
        'document': { icon: 'description', label: 'Document Mode', color: 'text-emerald-400', placeholder: 'Ask questions about your document…' }
    };

    appMode = modes[newMode] ? newMode : "chat";
    const config = modes[appMode];

    const badge = document.getElementById('mode-badge');
    if (badge) {
        badge.innerHTML = `<span class="material-symbols-outlined" style="font-size:12px">${config.icon}</span>${config.label}`;
        badge.className = `text-[10px] bg-white/5 border border-white/10 px-2 py-0.5 rounded-full uppercase tracking-widest flex items-center gap-1 transition-colors relative z-10 ${config.color}`;
    }

    const input = document.getElementById('chat-input');
    if (input) {
        input.placeholder = config.placeholder;
    }
}

// --- Document Upload ---
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        const sendIcon = document.getElementById("send-icon");
        const spinner = document.getElementById("send-loading");
        if (sendIcon) sendIcon.classList.add("hidden");
        if (spinner) spinner.classList.remove("hidden");

        uiShowToast("Uploading document...", "info");
        const res = await window.api.upload(file);
        uiShowToast("Document ready for analysis.", "success");

        uploadedDoc = { file: file, name: file.name, id: res.document_id || 'doc' };

        const preview = document.getElementById('doc-preview');
        const docName = document.getElementById('doc-name');
        if (preview && docName) {
            docName.innerText = file.name;
            preview.classList.remove('hidden');
            preview.classList.add('flex');
        }

        switchMode("document");

    } catch (e) {
        console.error("Upload failed", e);
        uiShowToast("Document upload failed.", "error");
    } finally {
        const sendIcon = document.getElementById("send-icon");
        const spinner = document.getElementById("send-loading");
        if (sendIcon) sendIcon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
        event.target.value = ''; // reset file input
    }
}

function clearDocument() {
    uploadedDoc = null;
    const preview = document.getElementById('doc-preview');
    if (preview) {
        preview.classList.add('hidden');
        preview.classList.remove('flex');
    }
    switchMode("chat");
}

function uiShowToast(msg, type) {
    if (window.ui && window.ui.showToast) window.ui.showToast(msg, type);
    else console.log(`[${type}] ${msg}`);
}

// --- V8 Mission Graph (Cytoscape) ---
function _renderMissionGraph(graphData) {
    if (!window.cytoscape) return;
    
    const elements = [];
    // 1. Add Nodes
    graphData.forEach(node => {
        elements.push({
            data: { 
                id: node.id, 
                label: node.agent.replace('_agent', '').toUpperCase(),
                agent: node.agent
            }
        });
    });

    // 2. Add Edges (Dependencies)
    graphData.forEach(node => {
        if (node.dependencies) {
            node.dependencies.forEach(dep => {
                elements.push({
                    data: { source: dep, target: node.id }
                });
            });
        }
    });

    if (!cy) {
        cy = cytoscape({
            container: document.getElementById('cy-container'),
            elements: elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#a855f7',
                        'label': 'data(label)',
                        'color': '#fff',
                        'font-size': '10px',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'width': '50px',
                        'height': '50px',
                        'font-family': 'Outfit'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#1e293b',
                        'target-arrow-color': '#1e293b',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier'
                    }
                }
            ],
            layout: { name: 'breadthfirst', directed: true, padding: 10 }
        });
    } else {
        cy.json({ elements: elements });
        cy.layout({ name: 'breadthfirst', directed: true, padding: 10 }).run();
    }
}

// Expose functions to window
window.switchMode = switchMode;
window.handleFileUpload = handleFileUpload;
window.clearDocument = clearDocument;
window.setMood = setMood;
window.handleKey = handleKey;
window.autoResize = autoResize;
window.clearChat = clearChat;
window.sendMessage = sendMessage;
window.submitFeedback = submitFeedback;
window.speakLast = speakLast;
window.startVoice = startVoice;
