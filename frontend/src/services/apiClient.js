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
 * Hardened POST SSE Streamer
 * Uses fetch + ReadableStream to support POST bodies for SSE.
 */
export const apiPostStream = async (path, body, { onToken, onEvent, onError }) => {
  const token = localStorage.getItem("fb_token");
  
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": token ? `Bearer ${token}` : "",
        "X-Trace-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // Keep partial line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.replace("data: ", "").trim();
          if (!jsonStr) continue;
          try {
            const data = JSON.parse(jsonStr);
            if (data.token && onToken) onToken(data.token);
            if (data.event && onEvent) onEvent(data.event, data);
          } catch (e) {
            console.warn("JSON parse error in stream", e);
          }
        }
      }
    }
  } catch (err) {
    console.error("Stream Error:", err);
    if (onError) onError(err);
  }
};

/**
 * Standard GET SSE Streamer
 * Uses Native EventSource for simpler GET streams (Neural Status, Stats).
 */
export const apiStream = (path, onMessage) => {
  const eventSource = new EventSource(`${BASE_URL}${path}`);
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.warn("SSE parse error", e);
    }
  };

  eventSource.onerror = (err) => {
    console.error("SSE connection failed", err);
    eventSource.close();
  };

  return () => eventSource.close();
};
