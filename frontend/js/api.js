const API_BASE = "http://127.0.0.1:8000";

export async function chat(message, session="user1") {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      session_id: session,
      message: message
    })
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return await res.json();
}

export async function searchQuotes(text) {
  const res = await fetch(`${API_BASE}/search_quotes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: text,
      top_k: 5
    })
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return await res.json();
}

export async function getDailyQuote() {
  const res = await fetch(`${API_BASE}/daily_quote`);
  if (!res.ok) throw new Error("Daily quote failed");
  return await res.json();
}

export async function getAnalytics() {
  const res = await fetch(`${API_BASE}/analytics`);
  if (!res.ok) throw new Error("Analytics failed");
  return await res.json();
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return await res.json();
}

export async function getFeed() {
  // Placeholder for feed logic
  return [];
}

export async function likeItem(id) {
  // Placeholder for like logic
  return { success: true };
}

export async function generateQuote(topic) {
  const res = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: topic
    })
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return await res.json();
}

