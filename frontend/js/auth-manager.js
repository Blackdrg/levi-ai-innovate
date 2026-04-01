/* frontend/js/auth-manager.js */
console.log("[LEVI] auth-manager.js executing...");

document.addEventListener('DOMContentLoaded', () => {
    // Sync UI on load
    const user = JSON.parse(localStorage.getItem('fb_user') || 'null');
    window.updateUIState(user);
    if (user && !window.levi_user_token) {
        window.levi_user_token = localStorage.getItem('fb_token');
    }
});

// ==========================================
// 1. Global UI State Sync
// ==========================================
window.updateUIState = (user) => {
    const navBtn = document.getElementById('nav-auth-btn');
    const creditsDisplay = document.getElementById('credits-display');
    const userDisplay = document.getElementById('user-display');

    if (user && navBtn) {
        navBtn.textContent = 'Account';
        navBtn.href = 'my-gallery.html';
        navBtn.classList.remove('btn-gold');
        navBtn.classList.add('ghost-border', 'px-6', 'py-2', 'text-zinc-300', 'hover:text-primary');
        
        if (userDisplay) {
            userDisplay.textContent = user.username || user.email;
        }
    } else if (navBtn) {
        navBtn.textContent = 'Sign In';
        navBtn.href = 'auth.html';
        navBtn.classList.add('btn-gold');
        navBtn.classList.remove('ghost-border', 'text-zinc-300');
    }

    if (creditsDisplay && user && user.credits !== undefined) {
        creditsDisplay.textContent = `${user.credits} units`;
        creditsDisplay.parentElement.classList.remove('hidden');
    }
};

// ==========================================
// 2. User State Synchronization
// ==========================================
window.syncUser = async () => {
    try {
        const data = await window.api.getMe();
        localStorage.setItem('fb_user', JSON.stringify(data));
        window.updateUIState(data);
        console.log("[LEVI] Profile synchronized.");
        return data;
    } catch (e) {
        console.warn("[LEVI] User sync failed:", e);
    }
};

// ==========================================
// 3. Authentication Actions
// ==========================================
window.handleLogin = async (email, password) => {
    try {
        // In a real production-ready app, we might still use Firebase Client SDK 
        // to get the ID Token, then pass it to our login endpoint for session verification.
        // For this transformation, we follow the "Connect UI to backend" rule.
        
        // 1. Firebase Login (Client Side) - Still needed for token generation in standard Firebase setups
        const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
        const token = await userCredential.user.getIdToken(true);
        
        // 2. Backend Handshake
        const res = await window.api.apiFetch("/auth/login", { 
            method: "POST", 
            body: { uid: userCredential.user.uid, email: email } 
        });

        // 3. Persistence
        localStorage.setItem('fb_token', token);
        window.levi_user_token = token;
        
        await window.syncUser();
        window.location.href = 'index.html';
    } catch (error) {
        console.error("Login failed:", error);
        throw error;
    }
};

window.handleSignup = async (email, password, username) => {
    try {
        // 1. Backend Signup (Creates user in Firebase via Admin SDK)
        const res = await window.api.signup(email, password, username);
        
        // 2. Login immediately after signup
        return window.handleLogin(email, password);
    } catch (error) {
        console.error("Signup failed:", error);
        throw error;
    }
};

window.logout = () => {
    if (typeof firebase !== 'undefined' && firebase.auth) {
        firebase.auth().signOut().then(() => { 
            localStorage.clear();
            window.location.href = 'auth.html'; 
        });
    } else {
        localStorage.clear();
        window.location.href = 'auth.html';
    }
};

// ==========================================
// 4. Token Waiter (Compatibility)
// ==========================================
window.waitForToken = () => {
    return new Promise((resolve) => {
        const token = localStorage.getItem('fb_token');
        if (token) resolve(token);
        else {
            // Fallback to Firebase observer if token not yet in storage
            const auth = typeof firebase !== 'undefined' ? firebase.auth() : null;
            if (!auth) { resolve("local-token"); return; }
            
            const unsubscribe = auth.onAuthStateChanged(async (u) => {
                unsubscribe();
                if (u) {
                    const t = await u.getIdToken(true);
                    localStorage.setItem('fb_token', t);
                    resolve(t);
                } else resolve("local-token");
            });
            setTimeout(() => { unsubscribe(); resolve("local-token"); }, 3000);
        }
    });
};
