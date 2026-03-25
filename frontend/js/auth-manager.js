/* frontend/js/auth-manager.js */

// ==========================================
// 1. Firebase Initialization & Configuration
// ==========================================
// TODO: Replace this object with your actual Firebase Project keys.
const firebaseConfig = {
  apiKey: "AIzaSyBkFj3B-YsG6MKyVbW_4jSF1VVoNSbP1UM",
  authDomain: "levi-ai-c23c6.firebaseapp.com",
  projectId: "levi-ai-c23c6",
  storageBucket: "levi-ai-c23c6.firebasestorage.app",
  messagingSenderId: "92414072890",
  appId: "1:92414072890:web:e0e824b7f339bf0ad9fd03",
  measurementId: "G-ST6N1X9RHD"
};

// Initialize Firebase only once
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const isLocal = ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(window.location.hostname) || window.location.port === '8080' || window.location.port === '5500';
window.API_BASE = isLocal ? `http://${window.location.hostname}:8000` : `${window.location.origin}/api`;

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
window.waitForToken = () => new Promise((resolve) => {
    // If we already have a token, resolve immediately
    if (window.levi_user_token) return resolve(window.levi_user_token);
    
    // Check if Firebase is even initialized
    if (!firebase.apps.length) return resolve(null);

    // Watch for the state change
    const unsub = firebase.auth().onAuthStateChanged(async (user) => {
        if (user) {
            window.levi_user_token = await user.getIdToken();
            unsub();
            resolve(window.levi_user_token);
        } else {
            unsub();
            resolve(null);
        }
    });

    // Safety timeout: don't hang if firebase takes too long
    setTimeout(() => {
        unsub();
        resolve(window.levi_user_token);
    }, 5000);
});

// ==========================================
// 3. Fetch API Interceptor for Firebase Admin
// ==========================================
const originalFetch = window.fetch;
window.fetch = async function () {
    let [resource, config] = arguments;
    const url = typeof resource === 'string' ? resource : (resource && resource.url ? resource.url : '');
    
    // Intercept if it's hitting our backend (port 8000 locally or /api in prod)
    if (url.startsWith(window.API_BASE) || url.includes(':8000/') || (url.includes('/api/') && !url.startsWith('http'))) {
        // Wait for auth to settle
        await window.waitForToken();
        
        if (!config) config = {};
        if (!config.headers) config.headers = {};
        
        // Ensure standard headers
        if (!config.headers['Content-Type'] && !(config.body instanceof FormData)) {
            config.headers['Content-Type'] = 'application/json';
        }
        
        config.credentials = 'include';
        
        if (window.levi_user_token) {
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
