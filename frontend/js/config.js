/* frontend/js/config.js */

// Firebase Configuration via CI/CD Placeholders
const firebaseConfig = {
  apiKey: "__FIREBASE_API_KEY__",
  authDomain: "__FIREBASE_AUTH_DOMAIN__",
  projectId: "__FIREBASE_PROJECT_ID__",
  storageBucket: "__FIREBASE_STORAGE_BUCKET__",
  messagingSenderId: "__FIREBASE_MESSAGING_SENDER_ID__",
  appId: "__FIREBASE_APP_ID__"
};

// Environment-Aware API Logic
const CONFIG = {
  getApiBase: () => {
    if (typeof window !== 'undefined') {
      const { hostname, origin } = window.location;
      // 1. Local Development
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000/api/v1';
      }
      // 2. Production (Supports Vercel & Firebase Hosting Rewrites)
      return `${origin}/api/v1`;
    }
    return '/api/v1';
  },
  firebase: firebaseConfig
};

// Global Exposure
if (typeof window !== 'undefined') {
  window.API_BASE = CONFIG.getApiBase();
  window.firebaseConfig = firebaseConfig;
  window.LEVI_CONFIG = CONFIG;
}
