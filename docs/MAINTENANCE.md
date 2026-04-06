# 🛠️ Maintenance Guide (v1.0.0-RC1)

Ensuring the stability and fidelity of the LEVI-AI v1.0.0-RC1 Distributed Stack requires periodic maintenance of the quad-persistence memory fabric.

---

## 🧠 1. Cognitive Memory Maintenance

### **Memory Crystallization (Automatic)**
The crystallization phase is triggered automatically every 10 missions.
- **Action:** Monitors the mission ledger in Postgres.
- **Manual Trigger:** Use `MemoryManager.force_crystallization(user_id)` for manual fact distillation.

### **Fact Distillation (Automatic)**
Fragmented episodic facts are distilled into permanent relational knowledge triplets.
- **Action:** Background Celery process that checks facts with **Importance > 0.8**.
- **Service:** `backend.core.memory_manager.trigger_distillation()`.

---

## 🗄️ 2. Persistence Layer Maintenance

### **FAISS Index Sync**
Semantic memory is stored in a localized FAISS index.
- **Recommendation:** Perform a periodic `VectorStore.rebuild_index()` for heavy-usage tenants to optimize retrieval accuracy.

### **Vault Key Rotation**
Encryption keys used by the Vault Service should be rotated periodically via the `backend/auth/logic.py` internal API.

---

## 📡 3. Resource Hygiene

### **Memory Pruning**
- **System:** `backend.core.memory_tasks.MemoryPruner`.
- **Action:** Weekly autonomous purge of low-importance memories (<0.5) to manage the local FAISS index footprint.
- **Audit:** Search for "pruning_cycle" in the Celery worker logs.

### **Redis Queue Flush**
Mission state keys are transient. They are cleared automatically upon completion. To prune orphaned keys:
- **Command:** `redis-cli --scan --pattern "mission:blackboard:*" | xargs redis-cli del`

---

## 📈 4. Performance Diagnostics
Use `pytest tests/v1_graduation_suite.py` to perform a 360-degree connectivity and fidelity audit.
- **KPI Thresholds:**
    - **API Latency:** < 500ms.
    - **Memory Retrieval:** < 100ms.
    - **Fidelity Score (S):** > 0.90 average.

---

© 2026 LEVI-AI SOVEREIGN HUB.
