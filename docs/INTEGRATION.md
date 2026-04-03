# 🔌 LeviBrain v8: High-Fidelity Integration Interface

Documentation for the **Sovereign Monolith** communication protocols, focusing on the refined v8 SSE (Server-Sent Events) pulse architecture and mission auditing.

---

## 📡 1. Deep Core v8 SSE Pulse Protocol

The LeviBrain v8 frontend (`React + Vite`) utilizes a high-fidelity streaming interface to track the 8-step cognitive pipeline in real-time.

### Event Lifecycle:
The `useStream.js` hook parses the following standardized v8 events:

| Event Type | Data Payload | UI Action |
|------------|--------------|-----------|
| `metadata` | `{request_id, session_id}` | Initializes transmission state. |
| `graph` | `{nodes, edges}` | Renders the topological **Execution Graph**. |
| `activity` | `{node_id, status, content}` | Updates node pulsing and partial results. |
| `audit` | `{fidelity, issues, fix}` | Spawns the **Mission Auditor** dashboard. |
| `done` | `{final_response}` | Closes the stream and commits to memory. |

### Implementation Example:
```javascript
// frontend/src/hooks/useStream.js
const event = line.replace('event: ', '');
const data = JSON.parse(line.replace('data: ', ''));

switch(event) {
  case 'graph': setExecutionGraph(data); break;
  case 'audit': setAuditResult(data); break;
  // ... update v8 high-fidelity states
}
```

---

## 🎥 2. Asynchronous Mission Handshake

For heavy generative tasks (Video/Large Document Analysis), the v8 orchestrator uses a hybrid SSE + Polling model.

1. **Mission Start:** `POST /api/v1/orchestrator/chat` yields an immediate `mission_id`.
2. **Cognitive Streaming:** The SSE stream provides real-time updates on task execution.
3. **Blob Delivery:** For file outputs (Image/Video), the `done` event contains the temporary or signed URL to the **Sovereign Cloud Storage**.

---

## 🌌 3. The `v8` Cognitive UI Mapping

The **Refinement Planner** dictates the visual display. If the v8 brain determines a transformation is required, it injects UI intents into the stream:

- **Graph Intent:** Triggers the glassmorphic `ExecutionGraph.jsx`.
- **Audit Intent:** Triggers the `MissionAuditor.jsx` with fidelity scoring.
- **Resonance Intent:** Adjusts the global CSS theme (e.g., `text-gradient-v8`) based on the brain's focus.

---

## 📊 4. Mission Fidelity Schema (v8)

Every completed mission returns a **Fidelity Bundle**:

```json
{
  "fidelity_score": 0.92,
  "metrics": {
    "alignment": 0.95,
    "grounding": 0.90,
    "resonance": 0.91
  },
  "audit": {
    "issues": ["Minor syntactic drift in node_4"],
    "fix_strategy": "Applied adaptive logic refinement."
  }
}
```
Missions with a score `< 0.85` automatically trigger a **Correction Wave** before final delivery.
