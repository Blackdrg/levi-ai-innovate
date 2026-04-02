/**
 * Sovereign Memory Vault v7. 
 * High-fidelity semantic explorer for crystallized patterns.
 * Components for searching, viewing, and pruning the Sovereign archive.
 */

class MemoryVault {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.render();
        this.loadCrystallizedFacts();
    }

    /**
     * Renders the basic structure of the Sovereign Vault.
     */
    render() {
        this.container.innerHTML = `
            <div class="sovereign-glass p-6 w-full max-w-4xl mx-auto mt-10">
                <header class="flex items-center justify-between mb-8 border-b border-white/5 pb-4">
                    <div>
                        <h2 class="text-2xl font-bold tracking-tight text-white mb-1">Memory Vault</h2>
                        <p class="text-xs text-slate-400 uppercase tracking-widest font-mono">Crystallized Intelligence</p>
                    </div>
                    <div class="bg-neural p-2 rounded-lg shadow-lg">
                        <span class="material-symbols-outlined text-white">psychology_alt</span>
                    </div>
                </header>

                <div class="flex flex-col gap-4" id="vault-list">
                    <!-- Facts will manifest here -->
                    <div class="flex justify-center p-12 opacity-50 italic text-sm">Synchronizing with the Sovereign Ledger...</div>
                </div>
            </div>
        `;
    }

    /**
     * Manifests the crystallized facts from the Sovereign backend.
     */
    async loadCrystallizedFacts() {
        const token = localStorage.getItem("sovereign_token");
        const listContainer = document.getElementById("vault-list");

        try {
            const resp = await fetch("/api/v1/memory/facts", {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (!resp.ok) throw new Error("Recall failed.");
            const data = await resp.json();
            
            listContainer.innerHTML = "";
            const facts = data.facts || [];

            if (facts.length === 0) {
                listContainer.innerHTML = `
                    <div class="p-8 text-center sovereign-glass bg-white/5 italic text-sm text-slate-400">
                        The archive is empty. Begin your journey to crystallize new patterns.
                    </div>
                `;
                return;
            }

            facts.forEach(fact => {
                const factDiv = document.createElement("div");
                factDiv.className = "flex items-start gap-4 p-4 sovereign-glass bg-white/5 sovereign-glass-hover mb-2";
                factDiv.innerHTML = `
                    <div class="mt-1">
                        <span class="material-symbols-outlined text-neural p-2 bg-white/5 rounded-lg text-lg">star</span>
                    </div>
                    <div class="flex-1">
                        <p class="text-white text-sm leading-relaxed">${fact.fact}</p>
                        <div class="flex items-center gap-3 mt-3">
                            <span class="text-[9px] uppercase tracking-widest text-slate-500 font-bold bg-white/5 px-2 py-0.5 rounded border border-white/5">${fact.category}</span>
                            <span class="text-[9px] text-slate-600 font-mono italic">${new Date(fact.learned_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                `;
                listContainer.appendChild(factDiv);
            });

        } catch (err) {
            console.error("[Vault] Neural recall failure:", err);
            listContainer.innerHTML = `<div class="p-4 text-center text-rose-400 text-sm italic font-mono uppercase tracking-widest border border-rose-500/30 bg-rose-500/5 rounded-lg">Recall Sequence Interrupted.</div>`;
        }
    }
}

// Global exposure
window.MemoryVault = MemoryVault;
