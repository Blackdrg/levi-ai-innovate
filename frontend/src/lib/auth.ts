/**
 * Sovereign Auth Logic v13.0.0.
 * Secure token management and automatic session persistence.
 */

export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function login(username: string, password: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  
  if (!res.ok) throw new Error("Sovereign identity check failed.");
  
  const { access_token, refresh_token } = await res.json();
  localStorage.setItem("token", access_token);
  localStorage.setItem("refresh", refresh_token);
  return access_token;
}

export async function apiFetch(endpoint: string, opts: RequestInit = {}) {
  let token = localStorage.getItem("token");
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  
  const getHeaders = (t: string | null) => ({
    ...opts.headers,
    "Content-Type": "application/json",
    ...(t ? { "Authorization": `Bearer ${t}` } : {}),
  });

  let res = await fetch(url, { ...opts, headers: getHeaders(token) });
  
  if (res.status === 401) {
    console.warn("[Auth] Token expired. Initiating JWTRotator refresh...");
    const refreshToken = localStorage.getItem("refresh");
    
    if (refreshToken) {
      try {
        const rr = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        
        if (rr.ok) {
          const { access_token } = await rr.json();
          localStorage.setItem("token", access_token);
          
          // Automatic retry with new identity token
          return await fetch(url, { ...opts, headers: getHeaders(access_token) });
        }
      } catch (err) {
        console.error("[Auth] Rotation failure:", err);
      }
    }
    
    // Fallback: Clear credentials on rotation failure
    localStorage.removeItem("token");
    localStorage.removeItem("refresh");
    window.location.href = "/auth"; // Redirect to re-establish identity
    throw new Error("Sovereign session expired.");
  }
  
  return res;
}
