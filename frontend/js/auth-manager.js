/* frontend/js/auth-manager.js */

// ==========================================
// 1. Firebase Initialization & Configuration
// ==========================================
// TODO: Replace this object with your actual Firebase Project keys.
// Configuration is now loaded from config.js
const firebaseConfig = window.firebaseConfig;

if (!firebaseConfig || !firebaseConfig.apiKey) {
    console.error("[LEVI] Firebase configuration missing! Ensure config.js is loaded.");
}

// Initialize Firebase only once
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const isLocal = window.location.hostname === "localhost";

window.API_BASE = isLocal
  ? "http://localhost:8000"
    : `${window.location.origin}/api`;   // ✅ Firebase rewrite handles routing

console.log(`[LEVI] API_BASE initialized: ${window.API_BASE}`);

window.levi_user_token = null;

// ==========================================
// 2. Centralized Auth State Manager
// ==========================================
firebase.auth().onAuthStateChanged(async (user) => {
    const pathname = window.location.pathname;
    const isAuthPage = pathname.endsWith('auth.html');
    const publicPages = ['index.html', 'auth.html', 'pricing.html', 'terms.html', 'privacy.html', '/', ''];
    const isPublic = publicPages.some(p => pathname.endsWith(p)) || pathname === '/' || pathname === '';

    if (user) {
        window.levi_user_token = await user.getIdToken(true);
        localStorage.setItem('levi_user', JSON.stringify({
            uid: user.uid, 
            email: user.email,
            username: user.displayName || user.email.split('@')[0]
        }));
        
        if (isAuthPage) {
            window.location.href = 'studio.html';
        }
    } else {
        window.levi_user_token = null;
        localStorage.removeItem('levi_user');
        
        if (!isPublic) {
            window.location.href = 'auth.html';
        }
    }
});

// Helper to wait for Firebase auth to initialize
window.waitForToken = () => {
    return new Promise((resolve) => {
        const user = firebase.auth().currentUser;
        if (user) {
            // Already logged in, just refresh token
            user.getIdToken(true)
                .then(token => {
                    window.levi_user_token = token;
                    resolve(token);
                })
                .catch(() => resolve(null));
        } else {
            // Wait for auth state change
            const unsubscribe = firebase.auth().onAuthStateChanged(async (u) => {
                unsubscribe();
                if (u) {
                    const token = await u.getIdToken(true);
                    window.levi_user_token = token;
                    resolve(token);
                } else {
                    resolve(null);
                }
            });
            // Safety timeout
            setTimeout(() => {
                unsubscribe();
                resolve(window.levi_user_token);
            }, 10000);
        }
    });
};

// ==========================================
// 3. Fetch API Interceptor for Firebase Admin
// ==========================================
const originalFetch = window.fetch;
window.fetch = async function () {
    let [resource, config] = arguments;
    const url = typeof resource === 'string' ? resource : (resource && resource.url ? resource.url : '');
    
    // Intercept if it's hitting our backend (port 8000 locally or /api in prod)
    if (url.startsWith(window.API_BASE) || url.includes(':8000/') || (url.includes('/api/') && !url.startsWith('http'))) {
        // Get fresh token (auto-refreshes if expired)
        const user = firebase.auth().currentUser;
        if (user) {
            try {
                const token = await user.getIdToken(); // false = use cached if valid, true = force refresh
                window.levi_user_token = token;
            } catch (err) {
                console.error("[LEVI] Failed to refresh token before fetch:", err);
            }
        }
        
        if (window.levi_user_token) {
            config.headers = config.headers || {};
            config.headers['Authorization'] = `Bearer ${window.levi_user_token}`;
        }
    }
    
    try {
         const response = await originalFetch(resource, config);
         if (response.status === 401 && !url.includes('/login') && !url.includes('/register')) {
             console.warn("[LEVI] Token rejected. Syncing auth state...");
             // Only redirect if we are sure we are logged out
             const user = firebase.auth().currentUser;
             if (!user) {
                 window.location.href = 'auth.html?expired=true';
             }
         }
         return response;
    } catch (err) {
         console.error(`[LEVI] Fetch error for ${url}:`, err);
         throw err;
    }
};

window.logout = () => {
    firebase.auth().signOut().then(() => {
        window.location.href = 'auth.html';
    });
};
