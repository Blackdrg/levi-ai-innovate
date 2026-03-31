/**
 * LEVI-AI Global UI Utilities
 * Phase 6: Production Hardened
 */

(function() {
    // Standardize Favorites (Local Storage for now)
    let favorites = JSON.parse(localStorage.getItem('levi_favorites') || '[]');

    function showToast(message, type = "info") {
        const existing = document.querySelector('.levi-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = `levi-toast fixed bottom-10 left-1/2 -translate-x-1/2 px-6 py-3 rounded-full glass border border-white/10 text-[11px] uppercase tracking-widest font-bold z-[100] animate-fade-up shadow-[0_10px_40px_rgba(0,0,0,0.5)]`;
        
        let color = 'text-primary';
        if (type === 'error') color = 'text-red-400';
        if (type === 'warning') color = 'text-yellow-400';
        if (type === 'success') color = 'text-emerald-400';
        
        toast.classList.add(color);
        toast.innerText = message;
        document.body.appendChild(toast);
        setTimeout(() => { if (toast.parentElement) toast.remove(); }, 4000);
    }

    // Global Loader Controls
    const loader = {
        show: () => {
            const l = document.getElementById('global-loader');
            if (l) { l.style.width = '30%'; l.style.opacity = '1'; }
        },
        finish: () => {
            const l = document.getElementById('global-loader');
            if (l) { 
                l.style.width = '100%';
                setTimeout(() => { l.style.opacity = '0'; setTimeout(() => l.style.width = '0', 300); }, 200);
            }
        }
    };

    // Dark Mode Initialization
    if (localStorage.getItem('darkMode') === 'true' || (!localStorage.getItem('darkMode') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    }

    // Export to window
    window.ui = {
        showToast,
        showError: (msg) => showToast(msg, "error"),
        showSuccess: (msg) => showToast(msg, "success"),
        showWarning: (msg) => showToast(msg, "warning"),
        showLoader: loader.show,
        finishLoader: loader.finish,
        toggleDarkMode: () => {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('darkMode', isDark);
        }
    };

    // Global Error Handlers
    window.addEventListener('unhandledrejection', (event) => {
        const error = event.reason || {};
        const msg = error.message || "Cosmic interference detected.";
        if (msg !== "UNAUTHORIZED") {
            window.ui.showToast(msg, "error");
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        // Init dark toggle listeners if they exist
        document.querySelectorAll('#dark-toggle').forEach(btn => {
            btn.addEventListener('click', window.ui.toggleDarkMode);
        });
        
        // Sync User if logged in
        if (window.syncUser) window.syncUser();
    });
})();
