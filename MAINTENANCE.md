# LEVI-AI: v6.8 "Sovereign" Maintenance & Lifecycle Guide 🛠️

This guide outlines the routine operational tasks for the self-evolving LEVI-AI v6.8 Sovereign platform.

---

## ⚙️ 1. The Sovereign Lifecycle (Celery)

The v6.8 engine manages intensive background tasks across two specialized queues.

| Task | Queue | Schedule | Purpose |
|:---|:---|:---|:---|
| `run_autonomous_evolution` | `default` | Daily (24h) | Mutates weak system prompts based on 5-star patterns. |
| `update_analytics_snapshot` | `default` | Every 4h | Flushes expensive aggregate counts to the dashboard cache. |
| `generate_video_task` | `heavy` | On-Demand | High-intensity cinematic video synthesis (600s timeout). |
| `flush_all_memory_buffers` | `default` | Every 30s | Syncs real-time interaction memory from Redis to Firestore. |
| `prune_expired_data` | `default` | Daily | Auto-cleans temp uploads and stale indices (Phase 6 Hardening). |
| `consolidate_global_wisdom`| `default` | Daily | Ensures Global Knowledge Index is persisted to disk regularly. |
| `cleanup_stuck_jobs` | `default` | Hourly | Auto-cleans Studio jobs lost in the 'processing' state. |

---

## 💾 2. The Memory Matrix (Redis & FAISS)

The 3-layer memory matrix is the core of LEVI's consciousness.

### Viewing Memory Health
```bash
# Check the status of the local FAISS index
ls -lh backend/data/memory/*.bin

# Verify the Redis-to-Firestore buffer depth
redis-cli LLEN memory_buffer:test_user
```

### Manual Index Maintenance
If the Global Wisdom index requires a refresh or if retrieval scores are drifting:
```bash
# Trigger a background maintenance cycle
celery -A backend.celery_app call backend.services.orchestrator.memory_tasks.run_global_maintenance
```

---

## 🛡️ 3. Prompt Mutation & Rollback

v6.8 uses an autonomous mutator. The "Original" prompt is always preserved in Firestore.

### Emergency Rollback
1.  Access Firestore: **`prompt_performance`** collection.
2.  Locate the failed variant (usually the one with a recent `evolved_at` timestamp).
3.  Copy the `original_prompt` back to the active array in `backend/learning.py`.
4.  Set `avg_score` to 5.0 to lock the variant from further mutation until re-evaluated.

---

## 🧪 4. Sovereign Health Diagnostics 👁️

LEVI v6.8 provides a deep diagnostic probe.

### Running the System Audit
Run the definitive smoke test to verify all 8-stage decision boundaries:
```bash
python tests/complete_verify_v6.py
```

### Real-Time Activity Monitoring
Subscribe to the Global Activity stream to witness the Meta-Brain's internal strategy:
```bash
# Using curl (SSE)
curl -N http://localhost/api/stream
```

---

## 💾 5. Local Engine (Sovereignty)

LEVI prioritizes non-cloud reasoning via local Llama-3-8B-Instruct.

- **Check Local Health**: The `/health` API will report `sovereign_v6: hardened` if the local route is active.
- **Model Upgrades**: When swapping `.gguf` files, ensure they are placed in the `models/` directory and `LOCAL_MODEL_PATH` is updated in `.env`.

---

**LEVI — Sovereign. Efficient. Self-Scaling.**
*Infinite Loop Initiated.*
