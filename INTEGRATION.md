# LEVI-AI: v5.0 Integration & API Reference 🚀

This document provides the definitive API reference and integration guide for the hardened LEVI-AI orchestrator.

---

## 📡 1. Primary Chat & Streaming API

The orchestrator combines `sanitization`, `memory`, `intent`, and `decision` into a single endpoint.

### `POST /api/v1/chat/message`
Primary message handler. Supports both synchronous and asynchronous (SSE) responses.

**Request Body (`application/json`):**
```json
{
    "message": "Write a python script for...",
    "session_id": "sess-456",
    "mood": "philosophical",
    "is_streaming": true
}
```

**Response (SSE Streaming):**
Chunks are sent with `data: ` prefix:
```text
data: {"token": "Hello", "intent": "greeting", "route": "local", "job_id": null}
data: {"token": " world", "intent": "greeting", "route": "local", "job_id": null}
data: {"token": "!", "intent": "greeting", "route": "local", "job_id": null}
data: [DONE]
```

---

## 🧠 2. Learning & Profile API

The learning system (`backend/services/learning/router.py`) allows AI personalization based on user interactions.

### `POST /api/v1/learning/feedback`
Submit rating (1-5) for an AI response. Updates the user's preference model and memory graph.

**Request Body:**
```json
{
    "session_id": "sess-456",
    "rating": 5,
    "user_message": "...",
    "bot_response": "..."
}
```

### `GET /api/v1/learning/profile` (Auth Required)
Returns the current learned AI profile for the authenticated user.
- **Includes**: `preferred_moods`, `system_prompt_preview`, `memory_graph_summary`.

---

## 📈 3. Decision Objects & Metadata

Every interaction returns structured metadata to the frontend.

### `DecisionLog` Structure
| Field | Type | Purpose |
|:---|:---|:---|
| `intent` | `string` | Result of `planner.py` (e.g., `greeting`, `image`, `code`). |
| `engine_route` | `string` | `local` (🟢), `tool` (🟡), or `api` (🔴). |
| `confidence` | `float` | AI confidence score in the routing decision. |
| `latency_ms` | `int` | Total processing time for the orchestrator. |

---

## 🛡️ 4. Integration Best Practices

1. **Handle SSE Appropriately**: Use `EventSource` (browser) or an SSE-aware HTTP client with `stream=True`.
2. **Badge UI**: Display the `engine_route` metadata with the corresponding color-coded badge (🟢/🟡/🔴) to communicate AI cost/depth to the user.
3. **Session Persistence**: Always provide a consistent `session_id` to enable mid-term memory (MTM) retrieval across interactions.

---

**LEVI — Built for emergence. Integrated for depth.**
