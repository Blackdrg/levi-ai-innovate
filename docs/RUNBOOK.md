# 🏃 Operational Runbook (v1.0.0-RC1)

Operations and maintenance procedures for the LEVI-AI v1.0.0-RC1 Local-First Distributed Stack.

---

## 🚀 1. Boot Procedure

1.  **Service Fabric:** Launch the core service infrastructure.
    ```powershell
    docker-compose up -d
    ```
2.  **Health Audit:** Perform the 28-point graduation verification.
    ```powershell
    pytest tests/v1_graduation_suite.py
    ```
3.  **Local Inference:** Ensure Ollama is running and models are pulled.
    ```powershell
    ollama list
    ```

---

## 🩺 2. System Health Audit

Perform a full connectivity and fidelity check across the quad-persistence layer.
```powershell
pytest tests/v1_graduation_suite.py -v
```
- **Checks:** Redis (Working Memory), Postgres (Episodic Memory), Neo4j (Knowledge Graph), and FAISS (Semantic Memory).

---

## 🛠️ 3. Emergency Recovery

### **State Sync Failure**
If the system enters an inconsistent state or mission blackboard is corrupted:
1.  **Flush Transient State:** `redis-cli flushall`.
2.  **Restart Services:** `docker-compose restart`. This re-initializes the Brain Controller mission loop.

### **Inference Latency Spikes**
If local inference waves exceed 15 seconds:
- **Action:** Check GPU utilization and system temperature.
- **Failover:** If local inference is stalled, ensure `CLOUD_FALLBACK_ENABLED=true` in `.env` if third-party inference is permissible.

---

© 2026 LEVI-AI SOVEREIGN HUB.
