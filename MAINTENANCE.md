# LEVI-AI: v6.8 "Sovereign" Maintenance & Lifecycle Guide 🛠️

This guide outlines the routine operational tasks for the self-evolving LEVI-AI v6.8 Sovereign platform.

---

## ⚙️ 1. The Sovereign Lifecycle (Celery)

The v6.8 engine manages intensive background tasks across two specialized queues.

| Task | Queue | Schedule | Purpose |
|:---|:---|:---|:---|
| `run_autonomous_evolution` | `default` | Daily (24h) | Mutates weak system prompts based on 5-star patterns. |
| `update_analytics_snapshot` | `default` | Every 4h | Flushes system health metrics to the dashboard cache. |
| `run_global_maintenance` | `heavy` | Daily | Consolidates FAISS indices and prunes orphaned memory vectors. |
| `flush_all_memory_buffers` | `default` | Every 30s | Syncs real-time interaction memory from Redis to Firestore. |
| `prune_expired_data` | `default` | Daily | Auto-cleans temp uploads and stale session data. |

---

## 💾 2. The Memory Matrix (Redis & FAISS)

The 3-layer memory matrix is the core of LEVI's consciousness.

### Viewing Memory Health
```bash
# Check the status of the local FAISS indices
ls -lh backend/data/memory/*.bin

# Verify model weight integrity
sha256sum backend/models/*.gguf
```

### Manual Index Maintenance
If retrieval scores are drifting or latency is increasing:
```bash
# Trigger a background maintenance cycle
celery -A backend.celery_app call backend.services.orchestrator.memory_tasks.run_global_maintenance
```

---

## 🛡️ 3. Prompt Mutation & Rollback

v6.8 uses an autonomous mutator to refine reasoning.

### Emergency Rollback
1.  Access Firestore: **`prompt_performance`** collection.
2.  Locate the failed variant (recent `evolved_at` timestamp).
3.  Revert the `active_prompt` to the `original_prompt` value.
4.  Restart the `levi-api` service to clear the prompt cache.

---

## 🧪 4. Sovereign Health Diagnostics 👁️

LEVI v6.8 provides a deep diagnostic probe.

### Running the Sovereignty Audit
Verify all 8-stage decision boundaries and local inference:
```bash
python tests/verify_sovereignty.py
```

### Real-Time Activity Monitoring
Subscribe to the Intelligence Pulse stream:
```bash
# Using curl (SSE)
curl -N http://localhost/api/stream | grep "type: activity"
```

---

## 💾 5. Local Engine (Sovereignty)

LEVI prioritizes non-cloud reasoning via local Llama-3-8B-Instruct.

- **Check Local Health**: The `/health` API will report `sovereign_v6: hardened` if the local route is active.
- **Model Upgrades**: When swapping `.gguf` files, ensure they are placed in the `models/` directory and `LOCAL_MODEL_PATH` is updated in `.env`.

---

**LEVI v6.8 — Sovereign. Efficient. Self-Scaling.**
*Infinite Learning Loop Hardened.*
