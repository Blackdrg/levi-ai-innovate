# 🛠️ LEVI-AI Sovereign Maintenance Guide (v9.8.1)

Ensuring the absolute fidelity of the LEVI-AI v9.8.1 "Sovereign Monolith" requires periodic maintenance of the cognitive data fabric.

---

## 🧠 1. Cognitive Memory Maintenance

### **Dreaming Phase (Automatic)**
The dreaming phase is triggered automatically every 5 missions.
- **Action:** Monitors the `sovereign:internal:mission_count` key in Redis.
- **Manual Trigger:** Use `DreamingTask.trigger_force(user_id)` for manual memory crystallization.

### **Trait Distillation (Automatic)**
Fragmented episodic facts are distilled into permanent traits.
- **Action:** Background process that checks facts with **Importance > 0.8**.
- **Service:** `backend.core.v8.memory_manager._trigger_distillation()`. (v13 SQL Resonance).

---

## 🗄️ 2. Persistence Layer Maintenance

### **FAISS Index Sync**
Semantic memory is stored in a partitioned FAISS index.
- **Recommendation:** Perform a weekly `SovereignVectorStore.rebuild_index()` for users with >10,000 interactions to optimize `HNSW` performance.

### **Postgres Identity Cleanup**
Encryption keys used by `SovereignVault` must be rotated annually via the `scripts/rotate_vault_keys.py` utility.

---

## 📡 3. Telemetry & Pulse Health

### **Survival Gating (Memory Hygiene)**
- **System:** `backend.services.learning.hygiene.SurvivalGater`.
- **Action:** Weekly autonomous purge of low-resonance memories (<0.5) to maintain HNSW index performance in FAISS.
- **Audit:** Search for "hygiene_cycle" in `learning_worker.py` logs.

### **Redis Pulse Flush**
The `sovereign:blackboard:{session_id}` keys are transient. They are cleared automatically upon mission completion, but it is recommended to perform a weekly `redis-cli --scan --pattern "sovereign:blackboard:*" | xargs redis-cli del` to prune any orphaned sessions.

---

## 📈 4. Performance Diagnostics
Use `scripts/verify_v9_8_full.py` to perform a 360-degree connectivity and fidelity audit.
- **Thresholds:**
    - **TTFT:** < 400ms.
    - **Memory Hydration:** < 200ms.
    - **Fidelity Score:** > 0.85 average.

---

© 2026 LEVI-AI SOVEREIGN HUB.
