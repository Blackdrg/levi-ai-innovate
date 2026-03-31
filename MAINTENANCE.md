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

**LEVI — Built for emergence. Hardened for scale. Sovereign by design.**
