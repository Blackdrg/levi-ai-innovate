/* frontend/js/config.js */

// Firebase Configuration template. 
// In production, these should be set during the build/deploy process.
const firebaseConfig = {
  apiKey: "AIzaSy...",            // your real key
  authDomain: "levi-ai-c23c6.firebaseapp.com",
  projectId: "levi-ai-c23c6",
  storageBucket: "levi-ai-c23c6.firebasestorage.app",
  messagingSenderId: "92414072890",
  appId: "1:92414072890:web:e0e824b7f339bf0ad9fd03"
};

// Environment Configuration
const CONFIG = {
  getApiBase: () => {
    if (typeof window !== 'undefined') {
      const { hostname, origin, protocol } = window.location;
      // 1. Local Development Fallback
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000/api/v1';
      }
      // 2. Production Dynamic Discovery (supports subdomains/Vercel/etc.)
      return `${origin}/api/v1`;
    }
    return '/api/v1'; // Generic fallback
  },
  firebase: firebaseConfig
};

// Export for app use
if (typeof window !== 'undefined') {
  window.firebaseConfig = firebaseConfig;
  window.LEVI_CONFIG = CONFIG;
}
