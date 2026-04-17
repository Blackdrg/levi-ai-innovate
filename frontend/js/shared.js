/**
 * LEVI-AI Shared UI & Navigation
 * Handles consistent sidebar/nav injection and common UI patterns.
 */

(function() {
    const NAV_ITEMS = [
        { name: 'Dashboard', url: 'index.html', icon: 'dashboard' },
        { name: 'Agents', url: 'agents.html', icon: 'smart_toy' },
        { name: 'Chat', url: 'chat.html', icon: 'chat' },
        { name: 'HITL', url: 'hitl.html', icon: 'pending_actions' },
        { name: 'Observability', url: 'observability.html', icon: 'monitoring' },
        { name: 'Learning', url: 'learning.html', icon: 'school' },
        { name: 'DR', url: 'dr.html', icon: 'restore' },
        { name: 'Studio', url: 'studio.html', icon: 'palette' },
        { name: 'Gallery', url: 'my-gallery.html', icon: 'photo_library' },
        { name: 'Admin', url: 'admin.html', icon: 'admin_panel_settings' }
    ];

    function injectNavigation() {
        const navContainer = document.getElementById('sovereign-nav');
        const sidebarContainer = document.getElementById('sovereign-sidebar');
        
        const currentPath = window.location.pathname.split('/').pop() || 'index.html';

        if (navContainer) {
            let navHtml = '';
            NAV_ITEMS.forEach(item => {
                const isActive = currentPath === item.url;
                const activeClass = isActive ? 'text-white border-b-2 border-neural font-bold' : 'text-slate-400 hover:text-white';
                navHtml += `
                    <a href="${item.url}" class="text-[10px] uppercase tracking-widest transition-colors flex items-center gap-1 ${activeClass} pb-1">
                        <span class="material-symbols-outlined text-sm">${item.icon}</span>
                        ${item.name}
                    </a>
                `;
            });
            navContainer.innerHTML = navHtml;
        }

        if (sidebarContainer) {
            let sidebarHtml = '';
            NAV_ITEMS.forEach(item => {
                const isActive = currentPath === item.url;
                const activeClass = isActive ? 'nav-active font-bold' : 'nav-inactive';
                sidebarHtml += `
                    <a href="${item.url}" class="${activeClass} flex items-center gap-4 px-4 py-3 rounded-r-xl text-xs uppercase tracking-widest">
                        <span class="material-symbols-outlined icon-sm ${isActive ? 'icon-fill' : ''}">${item.icon}</span>
                        ${item.name}
                    </a>
                `;
            });
            sidebarContainer.innerHTML = sidebarHtml;
        }
    }

    function renderAuditBadge(status, fidelity = 1.0, details = null) {
        const badges = {
            'VERIFIED': 'bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-400 border-emerald-500/30',
            'REVIEWED': 'bg-gradient-to-r from-blue-500/20 to-indigo-500/20 text-blue-400 border-blue-500/30',
            'DRAFT': 'bg-gradient-to-r from-orange-500/20 to-amber-500/20 text-orange-400 border-orange-500/30',
            'HALT': 'bg-gradient-to-r from-red-500/20 to-rose-500/20 text-red-400 border-red-500/30'
        };

        const config = badges[status] || badges['DRAFT'];
        const score = Math.round(fidelity * 100);
        
        let tooltip = '';
        if (details) {
            const issues = details.issues && details.issues.length > 0 ? details.issues.join(', ') : 'No alignment issues detected.';
            tooltip = `title="Confidence: ${score}% | Critique: ${issues}"`;
        }

        return `
            <span class="px-2 py-0.5 rounded-full border text-[8px] font-bold tracking-tighter uppercase cursor-help transition-all hover:scale-105 ${config}" ${tooltip}>
                ${status} <span class="ml-1 opacity-60">${score}%</span>
            </span>
        `;
    }

    async function submitFeedback(missionId, isPositive) {
        if (!missionId) return;
        try {
            const response = await fetch(`/api/v1/orchestrator/mission/${missionId}/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_positive: isPositive })
            });
            if (response.ok) {
                console.log(`✨ [Feedback] Reinforced mission ${missionId}`);
                // Visual feedback: find buttons and disable
                const container = document.querySelector(`.feedback-pulse[data-mid="${missionId}"]`);
                if (container) {
                    container.classList.add('opacity-40', 'pointer-events-none');
                }
            }
        } catch (e) {
            console.error('Feedback submission failed:', e);
        }
    }

    // Export helpers
    window.LeviUI = {
        injectNavigation,
        renderAuditBadge,
        submitFeedback
    };

    document.addEventListener('DOMContentLoaded', injectNavigation);
})();
