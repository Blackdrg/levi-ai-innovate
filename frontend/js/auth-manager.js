/* frontend/js/auth-manager.js */
console.log("[LEVI] auth-manager.js executing...");

// ==========================================
// 1. Firebase Initialization & Configuration
// ==========================================
const firebaseConfig = window.firebaseConfig;

if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    if (!firebaseConfig || !firebaseConfig.apiKey || firebaseConfig.apiKey.includes("__FIREBASE_")) {
        console.warn("[LEVI] Using Auth STUB (Local Mode)");
        window.firebase.auth = () => ({
            currentUser: { uid: "local-user", email: "local@example.com", getIdToken: async () => "local-token" },
            onAuthStateChanged: (cb) => { 
                const user = { uid: "local-user", email: "local@example.com", displayName: "Local Seeker" };
                cb(user); 
                return () => {}; 
            },
            signOut: async () => { console.log("Logged out from stub"); }
        });
    } else {
        try {
            firebase.initializeApp(firebaseConfig);
            console.log("[LEVI] Firebase Initialized.");
        } catch (e) {
            console.error("[LEVI] Firebase Init Failed:", e);
        }
    }
}

// ==========================================
// 2. Global UI State Sync
// ==========================================
window.updateUIState = (user) => {
    const navBtn = document.getElementById('nav-auth-btn');
    const creditsDisplay = document.getElementById('credits-display');
    const localUser = JSON.parse(localStorage.getItem('levi_user') || '{}');

    if (user && navBtn) {
        navBtn.textContent = 'Account';
        navBtn.href = 'my-gallery.html';
        navBtn.classList.remove('btn-gold');
        navBtn.classList.add('ghost-border', 'px-6', 'py-2', 'text-zinc-300', 'hover:text-primary');
    } else if (navBtn) {
        navBtn.textContent = 'Sign In';
        navBtn.href = 'auth.html';
        navBtn.classList.add('btn-gold');
        navBtn.classList.remove('ghost-border', 'text-zinc-300');
    }

    if (creditsDisplay && localUser.credits !== undefined) {
        creditsDisplay.textContent = `${localUser.credits} units`;
        creditsDisplay.parentElement.classList.remove('hidden');
    }
};

// ==========================================
// 3. User State Synchronization
// ==========================================
window.syncUser = async () => {
    try {
        if (!window.levi_user_token || window.levi_user_token === "local-token") return;
        
        const res = await originalFetch(`${window.API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${window.levi_user_token}` }
        });
        
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('levi_user', JSON.stringify(data));
            window.updateUIState(firebase.auth().currentUser || { uid: 'local' });
            console.log("[LEVI] User state synchronized.");
        }
    } catch (e) {
        console.warn("[LEVI] User sync failed:", e);
    }
};

// ==========================================
// 4. Token & Authorization
// ==========================================
window.waitForToken = () => {
    return new Promise((resolve) => {
        const isReady = typeof firebase !== 'undefined' && firebase.apps.length > 0;
        const auth = isReady ? firebase.auth() : null;
        if (!auth) { resolve("local-token"); return; }
        
        const user = auth.currentUser;
        if (user) {
            user.getIdToken(true).then(resolve).catch(() => resolve("local-token"));
        } else {
            const unsubscribe = auth.onAuthStateChanged(async (u) => {
                unsubscribe();
                if (u) resolve(await u.getIdToken(true));
                else resolve("local-token");
            });
            setTimeout(() => { unsubscribe(); resolve("local-token"); }, 5000);
        }
    });
};

// --- Auth State Interceptor ---
if (typeof firebase !== 'undefined' && firebase.auth) {
    try {
        firebase.auth().onAuthStateChanged(async (user) => {
            const isAuthPage = window.location.pathname.includes('auth.html');
            if (user) {
                window.levi_user_token = await user.getIdToken(true);
                await window.syncUser();
                
                // Smart Redirect: Move away from Auth page if logged in
                if (isAuthPage) {
                    window.location.href = 'my-gallery.html';
                }
            } else {
                window.levi_user_token = "local-token";
                localStorage.removeItem('levi_user');
                window.updateUIState(null);
            }
        });
    } catch(e) { console.error("[LEVI] Auth listener failed:", e); }
}

// --- Global Fetch Interceptor ---
const originalFetch = window.fetch;
window.fetch = async function (resource, config = {}) {
    const url = typeof resource === 'string' ? resource : (resource && resource.url ? resource.url : '');
    if (url.includes('/api/v1/') || url.includes(':8000/')) {
        config.headers = config.headers || {};
        if (typeof firebase !== 'undefined' && firebase.auth() && firebase.auth().currentUser) {
            try { window.levi_user_token = await firebase.auth().currentUser.getIdToken(); } catch (e) {}
        }
        config.headers['Authorization'] = `Bearer ${window.levi_user_token}`;
        config.headers['X-LEVI-Source'] = 'frontend-web';
    }
    return originalFetch(resource, config);
};

window.logout = () => {
    if (typeof firebase !== 'undefined' && firebase.auth) {
        firebase.auth().signOut().then(() => { 
            localStorage.clear();
            window.location.href = 'auth.html'; 
        });
    } else { window.location.href = 'auth.html'; }
};
