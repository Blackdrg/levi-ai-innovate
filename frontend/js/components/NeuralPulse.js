/**
 * Sovereign Neural Pulse v7. 
 * Real-time telemetry visualization for the LEVI-AI OS Evolution.
 * Components for monitoring neural activity and routing pulses.
 */

class NeuralPulse {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.pulses = [];
        this.maxPulses = 10;
        this.render();
        this.connectToSovereignPulse();
    }

    /**
     * Renders the basic telemetry dashboard.
     */
    render() {
        this.container.innerHTML = `
            <div class="sovereign-glass p-6 w-full max-w-4xl mx-auto mt-10">
                <header class="flex items-center justify-between mb-8">
                    <div>
                        <h2 class="text-2xl font-bold tracking-tight text-white mb-1">Neural Evolution</h2>
                        <p class="text-xs text-secondary-glow uppercase tracking-widest font-mono">Live Strategic Telemetry</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span id="pulse-status" class="w-3 h-3 bg-rose-500 rounded-full animate-pulse"></span>
                        <span class="text-[10px] text-slate-500 uppercase font-bold">Pulse Connection Active</span>
                    </div>
                </header>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" id="evolution-metrics">
                    <div class="sovereign-glass p-4 text-center bg-white/5 border border-white/5">
                        <p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Global Resonance</p>
                        <h3 class="text-3xl font-extrabold text-neural">0.88</h3>
                    </div>
                    <div class="sovereign-glass p-4 text-center bg-white/5 border border-white/5">
                        <p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Active Agents</p>
                        <h3 class="text-3xl font-extrabold text-white">14</h3>
                    </div>
                    <div class="sovereign-glass p-4 text-center bg-white/5 border border-white/5">
                        <p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Crystallizations</p>
                        <h3 class="text-3xl font-extrabold text-white">1,420</h3>
                    </div>
                </div>

                <div id="pulse-history" class="flex flex-col gap-3 font-mono">
                    <!-- Real-time activity pulses manifest here -->
                    <div class="text-center p-8 opacity-50 text-xs italic">Awaiting cosmic activity...</div>
                </div>
            </div>
        `;
    }

    /**
     * Establishes a secure connection to the Sovereign Intelligence Pulse (SSE).
     */
    connectToSovereignPulse() {
        const token = localStorage.getItem("sovereign_token");
        const eventSource = new EventSource(`/api/v1/pulse?token=${token}`);

        const historyContainer = document.getElementById("pulse-history");
        const statusDot = document.getElementById("pulse-status");

        eventSource.onopen = () => {
            statusDot.classList.replace("bg-rose-500", "bg-emerald-500");
            console.info("[Pulse] Sovereign Intelligence Link Established.");
        };

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.addPulse(data);
        };

        eventSource.onerror = (err) => {
            console.error("[Pulse] Link Severed. Retrying...", err);
            statusDot.classList.replace("bg-emerald-500", "bg-rose-500");
        };
    }

    /**
     * Manifests a new neural pulse in the activity history.
     */
    addPulse(pulse) {
        const historyContainer = document.getElementById("pulse-history");
        if (this.pulses.length === 0) historyContainer.innerHTML = "";

        this.pulses.unshift(pulse);
        if (this.pulses.length > this.maxPulses) this.pulses.pop();

        const pulseLine = document.createElement("div");
        pulseLine.className = "flex items-center gap-3 p-3 sovereign-glass bg-white/3 border border-white/5 animate-in opacity-0";
        pulseLine.style.animationFillMode = "forwards";
        
        const timestamp = new Date().toLocaleTimeString();

        pulseLine.innerHTML = `
            <span class="text-[10px] text-slate-600 font-bold">${timestamp}</span>
            <span class="text-[10px] text-neural font-bold uppercase tracking-widest bg-white/5 px-2 rounded-sm border border-white/5">${pulse.event || 'ACTIVITY'}</span>
            <span class="text-xs text-slate-300 flex-1 truncate">${JSON.stringify(pulse.data)}</span>
        `;
        
        historyContainer.prepend(pulseLine);
    }
}

// Global exposure
window.NeuralPulse = NeuralPulse;
