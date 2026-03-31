# LEVI-AI: v6.0 "Sovereign" Maintenance & Lifecycle Guide 🛠️

This guide outlines the routine operational tasks for the self-evolving LEVI-AI v6 platform.

---

## ⚙️ 1. The Revolution Lifecycle (Celery)

The v6 engine manages the "Dreaming" (Memory Distillation) and "Evolution" (Prompt Mutation) tasks.

| Task | Schedule | Purpose |
|:---|:---|:---|
| `evolve_system_prompts` | Interaction-based | Mutates low-performing prompts after 100 global 5-star ratings. |
| `distill_user_persona` | Every 20 interactions | Background task that consolidates user facts into high-level traits. |
| `prune_shared_patterns` | Weekly | Cleans up the anonymized collective wisdom pool to prevent drift. |
| `piston_heartbeat` | Every 5 min | Verifies Piston API sandbox health; toggles local fallback if failed. |

---

## 💾 2. The Reflex Ledger (Redis)

The real-time tool performance ledger is stored in Redis.

### Viewing Ledger Health
```bash
# Get success/failure stats for image_agent
redis-cli HGETALL ledger:agent:image_agent
```

### Resetting Metrics
If a tool enters a new version or fix, reset its metrics to allow the Meta-Brain to re-learn:
```bash
redis-cli DEL ledger:agent:image_agent
```

---

## 🛡️ 3. Prompt Versioning & Rollback

v6 stores the "Original" prompt in Firestore before any mutation.

### Emergency Rollback
If a mutated prompt results in degraded performance:
1.  Access Firestore: `prompt_performance` collection.
2.  Copy `original_prompt` back to the variant array in `backend/learning.py`.
3.  Set `avg_score` to 5.0 to prevent immediate re-mutation.

---

## 🧪 4. Sandbox Health (Piston API)

LEVI v6 uses the Piston API for secure execution.

- **Endpoint**: `https://emkc.org/api/v2/piston` (Default)
- **Monitoring**: If `piston_heartbeat` fails, LEVI logs a `CRITICAL` alert and switches to the restricted `LocalExecutor`.
- **Restoration**: Once the heartbeat returns, the system automatically restores the secure sandbox.

---

## 💾 5. Sovereign Vector Memory (FAISS)

The v6.8 "Hybrid Model" uses persistent FAISS indices for sub-millisecond semantic recall.

### Manual Index Rebuild
If the vector index becomes corrupted or requires a dimensionality shift:
```bash
# Trigger a background rebuild via Celery
celery -A backend.celery_app call backend.services.orchestrator.memory_tasks.run_global_maintenance
```

### Storage Paths
- **User Index**: `backend/data/memory/user_faiss.bin`
- **Global Wisdom**: `backend/data/memory/global_faiss.bin`
- **Metadata**: `backend/data/memory/*_meta.json`

---

## 🧠 6. Local Engine Lifecycle (GGUF)

LEVI prioritizes local reasoning via `llama-cpp-python`.

### Swapping Models
1.  Download a new `.gguf` model (e.g., Llama-3.1-8B-Instruct-Q4_K_M).
2.  Update `LOCAL_MODEL_PATH` in `.env`.
3.  Restart the backend worker.

### Health Check (Sovereignty)
Run the automated audit to verify routing logic:
```bash
python tests/verify_sovereignty.py
```

---

**LEVI — Built for emergence. Hardened for scale. Sovereign by design.**
