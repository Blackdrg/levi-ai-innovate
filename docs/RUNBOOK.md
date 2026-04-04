# 🏃 LEVI-AI Sovereign Runbook (v9.8.1)

Operations and cognitive maintenance procedures for the LEVI-AI v9.8.1 "Sovereign Monolith."

---

## 🚀 1. Cold Start Procedure
1.  **Orchestration Initializer:** Initialize the service fabric.
    ```bash
    docker-compose up -d postgres redis kafka zookeeper neo4j faiss firestore
    ```
2.  **Cognitive Migration:** Apply the v9.8.1 schema.
    ```bash
    python backend/core/v8/db_init.py
    ```
3.  **Monolith Boot:** Launch the API and Worker.
    ```bash
    uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
    python backend/workers/generative_worker.py
    ```

---

## 🩺 2. Diagnostic Verifications
Perform a 360-degree cognitive health check.
```bash
python scripts/verify_v9_8_full.py
```
- **Checks:** Redis context pulse, Postgres traits connection, Kafka event flow, Neo4j knowledge graph, and FAISS vector retrieval.

---

## 🛠️ 3. Emergency Recovery
### **"Quantum Misalignment" (State Sync Failure)**
If the brain enters an inconsistent state:
1.  **Flush Pulse Cache:** `redis-cli flushall`.
2.  **Restart Monolith:** Restart the API container to re-initialize the `MemoryManager`.

### **Agent Tool Latency High**
If agent execution waves exceed 15 seconds:
- **Action:** Check **Tavily/OpenAI** API health.
- **Circuit Breaker:** The `sovereign-breaker` should trigger automatically, but if it fails, manually set `ROUTING_OVERRIDE=local` in `.env` for zero-latency survival.

---

© 2026 LEVI-AI SOVEREIGN HUB.
