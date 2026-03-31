/* frontend/js/config.js */
/**
 * LEVI AI Frontend Configuration
 */

const firebaseConfig = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "your-project-id.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project-id.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef1234567890"
};

const CONFIG = {
  getApiBase: () => {
    const { hostname, origin } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return `${origin}/api/v1`;
  },
  firebase: firebaseConfig
};

if (typeof window !== 'undefined') {
  window.API_BASE = CONFIG.getApiBase();
  window.firebaseConfig = firebaseConfig;
  window.LEVI_CONFIG = CONFIG;
}
