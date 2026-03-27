/* frontend/js/config.js */

// Firebase Configuration template. 
// In production, these should be set during the build/deploy process.
const firebaseConfig = {
  apiKey: "REPLACE_WITH_YOUR_FIREBASE_API_KEY", // Loaded from environment or config at build time
  authDomain: "levi-ai-c23c6.firebaseapp.com",
  projectId: "levi-ai-c23c6",
  storageBucket: "levi-ai-c23c6.firebasestorage.app",
  messagingSenderId: "92414072890",
  appId: "1:92414072890:web:e0e824b7f339bf0ad9fd03",
  measurementId: "G-ST6N1X9RHD"
};

// Export for use in auth-manager.js
if (typeof window !== 'undefined') {
    window.firebaseConfig = firebaseConfig;
}
