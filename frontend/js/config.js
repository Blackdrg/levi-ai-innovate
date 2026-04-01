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
    const { hostname } = window.location;
    // 1. Local Development
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000';
    }
    // 2. Production (Sovereign Domain)
    return 'https://api.levi-ai.com';
  },
  firebase: firebaseConfig,
  isConfigured: () => {
    return firebaseConfig.apiKey && 
           !firebaseConfig.apiKey.includes("YOUR_FIREBASE") && 
           !firebaseConfig.apiKey.includes("__FIREBASE_");
  }
};

// Global Exposure & Validation
if (typeof window !== 'undefined') {
  window.API_BASE = CONFIG.getApiBase();
  window.firebaseConfig = firebaseConfig;
  window.LEVI_CONFIG = CONFIG;

  if (!CONFIG.isConfigured()) {
    console.warn("%c[LEVI-AI] Critical: Firebase credentials are not yet configured.", 
                 "color: #f2ca50; font-weight: bold; font-size: 12px;");
    console.info("Please update /frontend/js/config.js with your real Firebase keys.");
  }
}
