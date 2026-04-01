# LEVI-AI: v6.8.5 "Sovereign Monolith" Integration & API Reference 🚀

This document provides the definitive API reference for the hardened v6.8.5 LEVI-AI Sovereign Monolith.

---

## 📡 1. Unified Chat & Sovereign Pulse

The orchestrator combines `intent detection`, `vector memory matrix`, `Local Reasoning`, and `autonomous evolution` into a single, high-performance SSE stream with real-time intelligence pulses.

### `POST /api/chat`
Primary message handler. Supports both synchronous (JSON) and asynchronous (SSE) responses.

**Request Body (`application/json`):**
```json
{
    "message": "Analyze the sovereign architecture of my mind.",
    "session_id": "sess-v685",
    "mood": "philosophical",
    "stream": true
}
```

**Response (SSE Streaming):**
Chunks are sent with the `data: ` prefix. LEVI v6.8.5 delivers **Intelligence Pulses** before the core response to visualize the monolith's internal reasoning stages.

```text
# 1. Activity Pulse (Thinking heartbeat)
data: {"event": "activity", "data": "Analyzing sovereign intent..."}
data: {"event": "activity", "data": "Recalling private memory matrix..."}

# 2. Decision Metadata (Full routing sync)
data: {"event": "metadata", "data": {
    "intent": "chat", 
    "route": "LOCAL", 
    "engine_metadata": {"provider": "Monolith", "model": "Llama-3-8B.gguf", "latency": 0.04},
    "request_id": "req_monolith_f01"
}}

# 3. Content Chunks (LLM Tokens)
data: {"event": "choice", "data": "The"}
data: {"event": "choice", "data": " architecture"}

# 4. Finalization
data: [DONE]
```

---

## 🧠 2. Sovereignty & Memory Matrix

### `GET /api/status/sovereign` (Admin)
Deep diagnostic probe of sub-system health (LLM, FAISS, GCS FUSE).
*   **Headers**: `X-Admin-Key: <ADMIN_KEY>`

### `POST /api/privacy/clear-all`
**Absolute Purge**. Triggers an atomic wipe of Firestore facts, Redis history, and local FAISS indices for the current user. Ensures absolute data sovereignty.

---

## 🛡️ 3. Integration Best Practices

1. **Intelligent Status Heartbeat**: Use the `event: activity` messages to drive the "Sovereign Radar" animation in your UI (e.g., *“LEVI is recalling your history...”*).
2. **Sovereign Engine Badge**: Always render the `engine_metadata` to show the user they are being served by the **Local Monolith**.
3. **Trace IDs**: Log the `request_id` for every interaction to enable deep-pulse auditing via the `Sovereign Engine Probe`.

---

**LEVI v6.8.5 — Built for emergence. Integrated for depth. Sovereign by design.**
