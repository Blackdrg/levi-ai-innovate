# LEVI-AI: v6.8 "Sovereign" Integration & API Reference 🚀

This document provides the definitive API reference for the hardened v6.8 LEVI-AI orchestrator.

---

## 📡 1. Unified Chat & Sovereign Streaming

The orchestrator combines `intent detection`, `vector memory`, `Sovereign Reasoning`, and `autonomous execution` into a single, high-performance SSE stream.

### `POST /api/v1/chat`
Primary message handler. Supports both synchronous (JSON) and asynchronous (SSE) responses.

**Request Body (`application/json`):**
```json
{
    "message": "Philosophize on the nature of digital memory...",
    "session_id": "sess-456",
    "stream": true
}
```

**Response (SSE Streaming):**
Chunks are sent with the `data: ` prefix. LEVI v6.8 introduces **Intelligence Pulses** before the response begins to visualize the brain's internal reasoning stages.

```text
# 1. Activity Pulse (Real-time thinking updates)
data: {"type": "activity", "message": "Analyzing sovereign intent..."}
data: {"type": "activity", "message": "Hydrating FAISS memory matrix..."}
data: {"type": "activity", "message": "Executing local inference..."}

# 2. Decision Metadata (Full orchestrator decision)
data: {"metadata": {"intent": "chat", "route": "sovereign", "request_id": "orch_abc123"}}

# 3. Content Chunks (LLM Tokens)
data: {"choices": [{"delta": {"content": "Memory"}}]}
data: {"choices": [{"delta": {"content": " is"}}]}
data: [DONE]
```

---

## 🧠 2. Sovereignty & Memory API

### `GET /api/v1/memory/status`
Check the health and synchronization state of the local FAISS indices.

### `POST /api/v1/analytics/feedback`
Submit rating (0.0 - 1.0) for an AI response. Triggers the **Autonomous Learning Loop** and potential prompt mutation.

---

## 🛡️ 3. Integration Best Practices

1. **Intelligent Status Indicators**: Use the `type: activity` events to drive a "Thinking Pulse" in your UI (e.g., *“LEVI is recalling your history...”*).
2. **Sovereign Badges**: Always render the `route` metadata. LEVI v6.8 emphasizes the `sovereign` route for privacy and cost efficiency.
3. **Trace IDs**: Log the `request_id` for every interaction to enable deep-dive debugging via the **[DIAGNOSTICS_MASTER.md](DIAGNOSTICS_MASTER.md)**.

---

**LEVI v6.8 — Built for emergence. Integrated for depth. Sovereign by design.**
