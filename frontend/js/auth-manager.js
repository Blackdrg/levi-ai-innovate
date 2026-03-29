/* frontend/js/auth-manager.js */
console.log("[LEVI] auth-manager.js executing...");

// Define this early so it's always available
window.waitForToken = () => {
    return new Promise((resolve) => {
        const auth = typeof firebase !== 'undefined' ? firebase.auth() : null;
        if (!auth) {
            console.warn("[LEVI] Firebase Auth not available, resolving with local token");
            resolve("local-token");
            return;
        }
        const authObj = auth; // compatibility
        const user = authObj.currentUser;
        if (user) {
            user.getIdToken(true).then(resolve).catch(() => resolve("local-token"));
        } else {
            const unsubscribe = authObj.onAuthStateChanged(async (u) => {
                unsubscribe();
                if (u) {
                    const token = await u.getIdToken(true);
                    resolve(token);
                } else {
                    resolve("local-token");
                }
            });
            setTimeout(() => { unsubscribe(); resolve("local-token"); }, 5000);
        }
    });
};

// ==========================================
// 1. Firebase Initialization & Configuration
// ==========================================
const firebaseConfig = window.firebaseConfig;

if (!firebaseConfig || !firebaseConfig.apiKey) {
    console.error("[LEVI] Firebase configuration missing!");
}

if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    if (!firebaseConfig || firebaseConfig.apiKey === "REPLACE_WITH_YOUR_FIREBASE_API_KEY") {
        console.warn("[LEVI] Using Auth STUB (Local Mode)");
        window.firebase.auth = () => ({
            currentUser: { uid: "local-user", email: "local@example.com", getIdToken: async () => "local-token" },
            onAuthStateChanged: (cb) => { cb({ uid: "local-user", email: "local@example.com", displayName: "Local Seeker" }); return () => {}; },
            signOut: async () => { console.log("Logged out from stub"); }
        });
    } else {
        try {
            firebase.initializeApp(firebaseConfig);
        } catch (e) {
            console.error("[LEVI] Firebase Init Failed:", e);
        }
    }
}

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
window.API_BASE = isLocal ? `http://${window.location.hostname}:8000/api/v1` : `${window.location.origin}/api/v1`;

console.log(`[LEVI] API_BASE: ${window.API_BASE}`);

window.levi_user_token = "local-token";

if (typeof firebase !== 'undefined' && firebase.auth) {
    try {
        firebase.auth().onAuthStateChanged(async (user) => {
            if (user) {
                window.levi_user_token = await user.getIdToken(true);
                localStorage.setItem('levi_user', JSON.stringify({
                    uid: user.uid, email: user.email, username: user.displayName || user.email.split('@')[0]
                }));
            } else {
                localStorage.removeItem('levi_user');
            }
        });
    } catch(e) {}
}

// Fetch Interceptor
const originalFetch = window.fetch;
window.fetch = async function () {
    let [resource, config] = arguments;
    config = config || {};
    const url = typeof resource === 'string' ? resource : (resource && resource.url ? resource.url : '');
    
    if (url.startsWith(window.API_BASE) || url.includes(':8000/')) {
        config.headers = config.headers || {};
        config.headers['Authorization'] = `Bearer ${window.levi_user_token}`;
    }
    return originalFetch(resource, config);
};

window.logout = () => {
    if (typeof firebase !== 'undefined' && firebase.auth) {
        try {
            firebase.auth().signOut().then(() => { window.location.href = 'auth.html'; });
        } catch(e) { window.location.href = 'auth.html'; }
    } else {
        window.location.href = 'auth.html';
    }
};
