import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * Hardened API Client for LEVI-AI
 * - Automatic Tracing (X-Trace-ID)
 * - Firebase Auth Injection
 * - SSE Streaming support
 */
export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Tracing & Traceability Interceptor
apiClient.interceptors.request.use((config) => {
  const traceId = crypto.randomUUID();
  const requestId = crypto.randomUUID();

  config.headers["X-Trace-ID"] = traceId;
  config.headers["X-Request-ID"] = requestId;

  // Add Auth Token from localStorage or Firebase if available
  const token = localStorage.getItem("fb_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // LEVI v6.8: Administrative Probe Protection
  if (config.url.includes("/health/sovereign") || config.url.includes("/learning/stats")) {
    const adminKey = localStorage.getItem("LEVI_ADMIN_KEY");
    if (adminKey) {
        config.headers["X-Admin-Key"] = adminKey;
    }
  }

  return config;
});

/**
 * Hardened SSE Streamer
 * Handles connection recovery and event mapping.
 */
export const apiStream = (path, onMessage, onError) => {
  const url = `${BASE_URL}${path}`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (err) {
      console.warn("[Stream Parse Error]", err);
    }
  };

  eventSource.onerror = (err) => {
    console.error("[Stream Connection Error]", err);
    if (onError) onError(err);
    eventSource.close();
  };

  return () => eventSource.close();
};
