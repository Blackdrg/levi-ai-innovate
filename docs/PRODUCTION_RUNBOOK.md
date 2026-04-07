# LEVI-AI Production Runbook (v14.0 Production)

This document provides the standard operational procedures for the LEVI-AI system. 

## 🏗️ Service Dependency & Boot Order
To ensure proper state synchronization and system consistency, services must be started in the following order:

1.  **Redis**: Centralized state and task queue management.
2.  **Postgres**: Session and user data persistence.
3.  **Neo4j**: Knowledge Graph and relationship mapping.
4.  **Ollama**: Local inference engine (Wait for model loading).
5.  **FastAPI (Main Gateway)**: Orchestration and API layer.

---

## 🏗️ Disaster Recovery & Resilience
### Executing the Restore Drill
If a system failure occurs, verify the 300s RTO (Recovery Time Objective):
1.  Navigate to `backend/scripts/`.
2.  Run `python -m restore_drill`.
3.  Monitor the `[DR-Replay]` logs to ensure tasks are re-hydrated from the `sessions_aborted` ledger.

### Manual LoRA Promotion
To promote a new model adapter manually:
1.  Invoke the `LearningLoop.promote_adapter("adapter_name")` function.
2.  Verify that the `Modelfile.lora` is updated.
3.  Restart the Ollama service to hot-swap the inference weights.

---

## 🛡️ Security & Privacy Operations
### JWT Revocation
To revoke a compromised batch of JWTs:
-   Issue a `REVOKE_ALL` signal to the `MemoryAgent` with the target `user_id` or `jid_prefix`.
-   This triggers a blacklist update in Redis (TTL 24h).

### GDPR Erasure
To trigger a full data erasure for a user:
1.  Run `python -m backend.scripts.gdpr_purge --user_id <USER_ID>`.
2.  This will cascade delete data from Postgres, Neo4j, and the Vector Store (FAISS).

---

## 📈 Performance & Scaling
### Response to VRAM_PRESSURE Alert
An alert will trigger if VRAM headroom falls below 2GB:
1.  **Immediate Action**: The `GraphExecutor` will automatically pause new task dispatches.
2.  **Manual Intervention**: Review preferred models in the orchestrator configuration.

---

## 🧪 HITL & Human Review
To manually approve a queued HITL item:
1.  Navigate to the **System Dashboard** in the frontend.
2.  Review the `primary_score` vs `shadow_score` divergence.
3.  Accept or modify the response to trigger the final record in the `LearningLoop`.
