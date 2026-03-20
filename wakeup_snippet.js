// Add this to frontend/js/api.js at the top, after the API_BASE declaration.
// It pings the backend on page load so Render wakes up before the user
// makes their first real request (free tier sleeps after 15 min of inactivity).

async function wakeUpBackend() {
  if (isLocalDev) return; // No need locally
  try {
    console.log('[LEVI] Waking up Render backend...');
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    const data = await res.json();
    console.log('[LEVI] Backend awake:', data.status);
  } catch (e) {
    console.warn('[LEVI] Backend wake-up ping failed (may still be starting):', e.message);
  }
}

// Call immediately — this runs in background while page renders
wakeUpBackend();
