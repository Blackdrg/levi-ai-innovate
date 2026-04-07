# LEVI-AI Production Runbook (v13.1.0-Hardened)

This document provides the canonical operational procedures for the LEVI-AI Sovereign OS. 

## 🏗️ Service Dependency & Boot Order
To ensure proper state synchronization and cognitive coherence, services must be started in the following order:

1.  **Redis**: Sovereignty over shared state and task queues.
2.  **Postgres**: Mission and user persistence.
3.  **Neo4j**: Knowledge Graph and Relation mapping.
4.  **Ollama**: Local inference engine (Wait for model loading).
5.  **FastAPI (Main Gateway)**: Orchestration and API layer.

---

## 🏗️ Disaster Recovery & Resilience
### Executing the Restore Drill
If a system-wide failure occurs, verify the 300s RTO (Recovery Time Objective):
1.  Navigate to `backend/scripts/`.
2.  Run `python -m restore_drill`.
3.  Monitor the `[DR-Replay]` logs to ensure missions are re-hydrated from the `missions_aborted` ledger.

### Manual LoRA Promotion
To promote a new model adapter manually:
1.  Call the `LearningLoop.promote_adapter("adapter_name")` method.
2.  Verify that the `Modelfile.lora` is updated.
3.  Restart the Ollama service to hot-swap the inference weights.

---

## 🛡️ Security & Privacy Operations
### JWT Revocation
To revoke a compromised batch of JWTs:
-   Issue a `REVOKE_ALL` pulse to the `MemoryAgent` with the target `user_id` or `jid_prefix`.
-   This triggers a blacklist update in Redis (TTL 24h).

### GDPR Erasure
To trigger a full data erasure for a user:
1.  Run `python -m backend.scripts.gdpr_purge --user_id <USER_ID>`.
2.  This will cascade delete from Postgres, Neo4j, and the Vector Store (FAISS/Qdrant).

---

## 📈 Performance & Scaling
### Response to VRAM_PRESSURE Alert
An alert will trigger if VRAM headroom falls below 2GB:
1.  **Immediate Action**: The `GraphExecutor` will pause new mission dispatches automatically.
2.  **Manual Intervention**: Shift the `preferred_model` in the [ModelRouter](file:///d:/LEVI-AI/backend/core/v8/brain.py) from 70B to 8B for non-critical agents.

---

## 🧪 HITL & Human Review
To manually approve a queued HITL item:
1.  Navigate to the **HITL Dashboard** in the frontend.
2.  Review the `primary_score` vs `shadow_score` divergence.
3.  Accept or modify the response to trigger the final crystallization in the `LearningLoop`.
