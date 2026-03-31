/**
 * LEVI-AI System Status Monitor
 * Phase 6: Production Health Check
 */

(function() {
    const POLL_INTERVAL = 30000; // 30 seconds
    const statusDot = document.getElementById("status-dot");
    const statusLabel = document.getElementById("status-label");

    async function updateStatus() {
        try {
            const data = await window.api.getStatus();
            
            if (statusDot && statusLabel) {
                statusDot.className = "w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]";
                const routeDist = data.orchestration?.route_distribution || {};
                const total = (routeDist.local || 0) + (routeDist.api || 0) + (routeDist.cache || 0);
                statusLabel.innerText = total > 0 ? "Celestial Link: Active" : "Celestial Link: Online";
            }
        } catch (e) {
            console.warn("[LEVI] Status poll failed", e);
            if (statusDot && statusLabel) {
                statusDot.className = "w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse";
                statusLabel.innerText = "Connection: Degraded";
            }
        }
    }

    // Initial check
    setTimeout(updateStatus, 1000);
    
    // Polling
    setInterval(updateStatus, POLL_INTERVAL);
})();
