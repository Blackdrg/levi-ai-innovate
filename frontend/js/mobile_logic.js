/**
 * LEVI-AI Sovereign OS v14.0.0 
 * Mobile Dashboard Logic & Telemetry Bridge
 */

const state = {
    isLinked: false,
    token: localStorage.getItem('sovereign_token'),
    activeMissionId: null,
    events: [],
    traits: [],
    patches: 0
};

// --- INITIALIZATION ---
window.addEventListener('load', () => {
    checkLinkStatus();
    if (state.token) {
        initTelemetryStream();
        loadCrystallizedTraits();
    } else {
        togglePairing(true);
    }
});

function checkLinkStatus() {
    const statusEl = document.getElementById('link-status');
    if (state.token) {
        statusEl.innerHTML = `
            <div class="w-2 h-2 rounded-full bg-emerald-500 pulse"></div>
            <span class="text-xs font-medium text-zinc-400">Linked</span>
        `;
        state.isLinked = true;
    } else {
        statusEl.innerHTML = `
            <div class="w-2 h-2 rounded-full bg-zinc-600"></div>
            <span class="text-xs font-medium text-zinc-500">Unlinked</span>
        `;
        state.isLinked = false;
    }
}

function togglePairing(show) {
    const overlay = document.getElementById('pairing-overlay');
    if (show) {
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
    } else {
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
    }
}

// --- SOVEREIGN LINK PROTOCOL ---
async function confirmLink() {
    const tokenInput = document.getElementById('token-input');
    const token = tokenInput.value.trim();
    
    if (!token) return;

    try {
        // v14.0.0 Sovereign OS Link
        const response = await fetch('/api/v1/mobile/link/confirm?token=' + token, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'linked') {
            localStorage.setItem('sovereign_token', data.secret);
            state.token = data.secret;
            state.isLinked = true;
            togglePairing(false);
            checkLinkStatus();
            initTelemetryStream();
            addEvent('System', 'Sovereign Link v14.0.0 Established.', 'settings_input_antenna');
        } else {
            alert('Pairing Failed: Link rejected by Sovereign OS.');
        }
    } catch (err) {
        console.error('Pairing Error:', err);
        alert('Pairing Error: Neural synchronization anomaly.');
    }
}

// --- ADAPTIVE PULSE DECODER (v5.0) ---
function decodePulse(rawData) {
    if (!rawData) return null;
    try {
        // 1. Try standard JSON first
        return JSON.parse(rawData);
    } catch (e) {
        // 2. Fallback to zlib decompression (Mobile Adaptive Mode)
        try {
            const binaryString = window.atob(rawData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            const decompressed = pako.inflate(bytes, { to: 'string' });
            return JSON.parse(decompressed);
        } catch (err) {
            console.error("[Pulse v5.0] Logic Drift: Decompression failure.", err);
            return null;
        }
    }
}

// --- TELEMETRY STREAM (SSE) ---
function initTelemetryStream() {
    console.log("[Pulse v5.0] Synchronizing v14.0.0 Sovereign OS Bridge...");
    
    // Request the graduated v1 telemetry stream
    const eventSource = new EventSource('/api/v8/telemetry/stream?profile=mobile&version=v14.0.0');

    // v14.0.0 Handshake
    eventSource.addEventListener('pulse_handshake', (e) => {
        const data = decodePulse(e.data);
        if (!data) return;
        console.log(`[Pulse v5.0] v14.0.0 Linked. Profile: ${data.profile}`);
        addEvent('System', `Sovereign OS Pulse v${data.version} established.`, 'terminal');
    });

    // Perception & Handoff (v14.0.0)
    eventSource.addEventListener('perception', (e) => {
        const event = decodePulse(e.data);
        if (!event) return;
        const { decision, metrics } = event.data;
        
        // Update Handoff UI
        const handoffEl = document.getElementById('handoff-status');
        if (metrics.handoff_active || metrics.local_handoff) {
            handoffEl.classList.remove('opacity-0');
            const provider = metrics.handoff_provider || (metrics.local_handoff ? 'Local' : 'Swarm');
            handoffEl.querySelector('span:last-child').innerText = `Neural Handoff: ${provider}`;
        } else {
            handoffEl.classList.add('opacity-0');
        }

        addEvent('Brain', `Perception: ${decision} path elected (v14.0.0)`, 'visibility');
    });

    // Learning & Self-Correction
    eventSource.addEventListener('learning_feedback', (e) => {
        const outcome = decodePulse(e.data);
        if (!outcome) return;
        if (!outcome.success) {
            addEvent('Evolution', `Failure detected in ${outcome.intent}. Healing active.`, 'build');
        }
    });

    eventSource.addEventListener('rule_promoted', (e) => {
        const data = decodePulse(e.data);
        if (!data) return;
        addEvent('Evolution', `New rule promoted: ${data.query.substring(0, 20)}...`, 'auto_fix_high');
        loadCrystallizedTraits(); 
    });

    // v14.0.0: Mission Events
    eventSource.addEventListener('mission_start', (e) => {
        const event = decodePulse(e.data);
        if (event) handleMissionUpdate({ type: 'mission_start', payload: event.data });
    });

    eventSource.addEventListener('mission_complete', (e) => {
        const event = decodePulse(e.data);
        if (event) handleMissionUpdate({ type: 'mission_complete', payload: event.data });
    });

    eventSource.addEventListener('mission_error', (e) => {
        const event = decodePulse(e.data);
        if (event) handleMissionUpdate({ type: 'mission_error', payload: event.data });
    });

    eventSource.addEventListener('activity', (e) => {
        const event = decodePulse(e.data);
        if (event) addEvent('Brain', event.data, 'bolt');
    });

    eventSource.addEventListener('graph', (e) => {
        const event = decodePulse(e.data);
        if (event && event.data) {
             const graphSize = Object.keys(event.data.nodes || {}).length;
             handleMissionUpdate({ type: 'mission_start', payload: { graph_size: graphSize } });
        }
    });

    eventSource.addEventListener('results', (e) => {
        const event = decodePulse(e.data);
        if (event) handleMissionUpdate({ type: 'mission_complete', payload: event.data });
    });

    // v14.0.0: Dreaming Phase Logs
    eventSource.addEventListener('MEMORY_DREAMING_START', (e) => {
        addEvent('Evolution', 'Sovereign Dreaming initiated: Consolidating episodic fragments...', 'psychology');
    });

    eventSource.addEventListener('MEMORY_DREAMING_COMPLETE', (e) => {
        addEvent('Evolution', 'Dreaming Phase successful. Traits crystallized.', 'auto_fix_high');
        loadCrystallizedTraits();
    });

    eventSource.onerror = (err) => {
        console.error("[Pulse v5.0] Bridge Severed. Recalibrating...", err);
        const statusIcon = document.getElementById('link-status').querySelector('div');
        statusIcon.classList.replace('bg-emerald-500', 'bg-rose-500');
    };
}

async function loadCrystallizedTraits() {
    try {
        const response = await fetch('/api/v8/telemetry/crystallized-traits');
        const data = await response.json();
        state.traits = data.traits || [];
        renderEvolutionGrid();
    } catch (err) {
        console.error("Failed to load traits:", err);
    }
}

function renderEvolutionGrid() {
    const grid = document.getElementById('evolution-grid');
    const patchCountEl = document.getElementById('patch-count');
    
    patchCountEl.innerText = `${state.traits.length} Intelligence Points`;
    
    // Clear dynamic entries but keep placeholders if needed
    // For simplicity, we just rebuild it
    let html = `
        <div class="p-3 rounded-2xl bg-white/5 border border-white/5 glass flex flex-col gap-1">
             <span class="text-[8px] text-zinc-500 uppercase font-bold">Fragility</span>
             <span class="text-xs font-semibold text-zinc-300">Stable (0.05)</span>
        </div>
    `;

    state.traits.slice(0, 3).forEach(trait => {
        html += `
            <div class="p-3 rounded-2xl bg-gold-500/5 border border-gold-500/10 glass flex flex-col gap-1 animate-fade-in">
                 <span class="text-[8px] text-gold-500/80 uppercase font-bold">Crystallized</span>
                 <span class="text-xs font-semibold text-zinc-200 truncate">${trait.trait}</span>
            </div>
        `;
    });

    grid.innerHTML = html;
}

function handleMissionUpdate(event) {
    const { type, payload } = event;
    
    switch (type) {
        case 'mission_start':
            updateMissionStatus('ACTIVE', 'gold');
            document.getElementById('mission-input').innerText = payload.input || "Analyzing mission graph...";
            document.getElementById('graph-container').innerHTML = generateGraphHTML(payload.graph_size);
            addEvent('Core', `Mission Started: ${payload.graph_size} nodes polarized.`, 'bolt');
            break;
            
        case 'task_complete':
            updateNodeStatus(payload.id, payload.success ? 'success' : 'failed');
            addEvent(payload.agent, `Node ${payload.id} resolved in ${payload.latency}ms.`, payload.success ? 'check_circle' : 'error');
            break;
            
        case 'mission_complete':
            updateMissionStatus('COMPLETE', 'emerald');
            addEvent('Core', 'Mission finalized. Synthesis successful.', 'verified');
            break;
            
        case 'mission_aborted':
            updateMissionStatus('ABORTED', 'rose');
            addEvent('Alert', `Mission aborted: ${payload.reason}`, 'warning');
            break;
    }
}

// --- UI UPDATES ---
function updateMissionStatus(text, color) {
    const statusEl = document.getElementById('mission-status');
    statusEl.innerText = text;
    statusEl.className = `px-2 py-0.5 rounded text-[10px] bg-${color}-500/20 text-${color}-400 font-bold uppercase tracking-wider`;
}

function generateGraphHTML(count) {
    // Generate simplified wave graph
    let html = '';
    for (let i = 0; i < Math.min(count, 5); i++) {
        html += `
            <div id="node-${i}" class="mission-node w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                <span class="material-symbols-outlined text-[16px] text-zinc-500">hub</span>
            </div>
            ${i < Math.min(count, 5) - 1 ? '<div class="w-4 h-[1px] bg-zinc-800"></div>' : ''}
        `;
    }
    return html;
}

function updateNodeStatus(nodeId, status) {
    // We map node IDs to the index for visualization
    const idx = parseInt(nodeId.split('_').pop()) || 0;
    const nodeEl = document.getElementById(`node-${idx}`);
    if (nodeEl) {
        nodeEl.classList.add(status);
        const icon = nodeEl.querySelector('span');
        if (status === 'success') icon.innerText = 'check_circle';
        if (status === 'failed') icon.innerText = 'error';
    }
}

function addEvent(source, msg, icon) {
    const feed = document.getElementById('event-feed');
    const eventEl = document.createElement('div');
    eventEl.className = 'flex gap-4 items-start p-4 rounded-2xl bg-white/5 border border-white/5 glass animate-fade-in';
    
    const colors = {
        'Core': 'gold',
        'System': 'cyan',
        'Alert': 'rose'
    };
    const color = colors[source] || 'zinc';

    eventEl.innerHTML = `
        <div class="w-8 h-8 shrink-0 rounded-full bg-${color}-500/10 flex items-center justify-center">
            <span class="material-symbols-outlined text-${color}-400 text-sm">${icon}</span>
        </div>
        <div class="flex-1 space-y-1">
            <div class="flex items-baseline justify-between">
                <span class="text-xs font-bold text-zinc-300">${source}</span>
                <span class="text-[9px] text-zinc-500">Now</span>
            </div>
            <p class="text-[11px] text-zinc-400 leading-relaxed">${msg}</p>
        </div>
    `;
    
    feed.prepend(eventEl);
    
    // Limit log to 10 events
    if (feed.children.length > 10) {
        feed.removeChild(feed.lastChild);
    }
}
