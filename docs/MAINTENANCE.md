# LEVI-AI: v6.8.5 "Sovereign Monolith" Maintenance & Lifecycle Guide 🛠️

This guide outlines the routine operational tasks for the self-evolving LEVI-AI v6.8.5 Sovereign Monolith.

---

## ⚙️ 1. The Monolithic Lifecycle (Background Tasks)

The v6.8.5 engine manages intensive background tasks using its internal `MonolithScheduler` and protected maintenance routes.

| Task | Trigger | Purpose |
|:---|:---|:---|
| `distill_core_memory` | Daily (02:00) | Distills fragmented facts into high-fidelity 'Persona Traits' for the User Matrix. |
| `autonomous_prompt_mutation` | Performance-Based | Mutates weak system instructions based on 5-star resonance scores. |
| `faiss_garbage_collection` | Weekly | Prunes orphaned vector clusters from the GCS FUSE mount to maintain sub-ms retrieval. |
| `heartbeat_synchronization` | Every 5 min | Checks the health of the 8Gi RAM perimeter and the Llama-3-8B local model. |

---

## 💾 2. The Memory Matrix (FAISS & GCS FUSE)

The Sovereign Memory Matrix is stored at `/mnt/vector_db` via GCS FUSE.

### Monitoring Memory Health
```bash
# Verify GCS FUSE mount point integrity
ls -lh /mnt/vector_db/users/

# Check specific user index size
du -sh /mnt/vector_db/users/<user_id>/index.faiss
```

### Manual Matrix Optimization
If retrieval latency exceeds 50ms:
```bash
# Manually trigger a maintenance cycle (Requires INTERNAL_SERVICE_KEY)
curl -X POST -H "X-Internal-Service-Key: <key>" https://levi-monolith/api/admin/memory/gc
```

---

## 🛡️ 3. Prompt Evolution & Rollback

v6.8.5 uses the `AdaptivePromptManager` to refine its own reasoning core.

### Emergency Evolution Rollback
1.  Access Firestore: **`prompt_performance`** collection.
2.  Locate the variant with the lowest consistency score.
3.  Set its `status` to `decommissioned`.
4.  The system will automatically fallback to the `universal_baseline` in the next interaction.

---

## 🧪 4. Absolute Privacy & Memory Wipes 👁️

LEVI-AI v6.8.5 enforces **Absolute Data Sovereignty**.

### Executing a Full Purge
When a user requests to be forgotten:
1.  The system performs an atomic delete across:
    - **Firestore**: User facts and persona traits.
    - **Redis**: Full conversation history and session context.
    - **GCS FUSE**: The binary FAISS index file at `/mnt/vector_db/users/<user_id>/`.
2.  Verification: `ls /mnt/vector_db/users/<user_id>/` should return 404.

---

## 🛠️ 5. Diagnostic Command Center

```bash
# Run the v6.8.5 production verification suite
python scripts/verify_production.py --prod

# Check the Sovereign Engine heart rate
curl -H "X-Admin-Key: <key>" https://levi-monolith/health/sovereign

# Monitor the real-time Intelligence Pulse
tail -f logs/orchestrator_pulse.log
```

---

**LEVI v6.8.5 — Sovereign. Efficient. Self-Scaling.**
*Collective Wisdom Distillation Hardened.*
