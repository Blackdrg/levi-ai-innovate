# 🚢 LEVI-AI Sovereign Monolith Deployment Architecture (v9.8.1)

> [!IMPORTANT]
> **LeviBrain v9.8.1 "Sovereign Monolith" Specification**
> LEVI-AI has transitioned to a High-Fidelity **Unified Cognitive Monolith**. The distributed microservice architecture (Kafka/Zookeeper) is deprecated. All cognitive operations (Perception, Planning, Execution, Reflection) now occur within a single high-performance **API Container** backed by a **Redis Pulse Bus** and **Postgres Sovereignty Store**.

---

## 🏗️ 1. Infrastructure Topology (v9.8.1)

The v9.8.1 Monolith uses a topological wave execution model with a simplified, low-latency service fabric.

```mermaid
graph TD
    LB[Sovereign Load Balancer] --> HTTPS
    HTTPS --> Web[React / SPA Frontend]
    HTTPS --> V8[LeviBrain v9.8.1 Monolith API]
    
    %% Service Fabric
    V8 -->|Identity & Audit| Postgres[(Postgres: SQL Fabric)]
    V8 -->|Pulse & Blackboard| Redis[(Redis: Neural Pulse v4.1)]
    V8 -->|Relational Knowledge| Neo4j[(Neo4j: Resonant Graph)]
    V8 -->|Cognitive Memory| FAISS[[HNSW Vault: Semantic Vault]]
    
    %% Async Loops
    Redis --> Worker[Background Dreaming & Evolution]
    Worker --> V8
```

---

## ⚙️ 2. Hardware Matrix Recommendations (v9.8.1)

Unified specs for the monolithic container.

| Node Type | Minimum Spec | Recommended Spec | Primary Role |
|-----------|--------------|------------------|--------------|
| **Sovereign Monolith** | 8 vCPU, 16GB RAM | 16 vCPU, 32GB RAM | Perception, DAG Execution, Swarm Consensus, and Dreaming. |
| **Sovereignty Store** | 2 vCPU, 4GB RAM | 4 vCPU, 8GB RAM | Postgres persistent rules and user identity. |
| **Neural Pulse Bus** | 1 vCPU, 2GB RAM | 2 vCPU, 4GB RAM | Redis-backed SSE telemetry and Mission Blackboard. |
| **Semantic Vault** | 2GB RAM | 8GB RAM | FAISS vector indices and trait crystallization. |

---

## ☁️ 3. Deployment & Monolith Boot

### Unified Container Graduation (Docker)
The v9.8.1 deployment is streamlined into a single backend image:
1. **Initialize Core:** Run the `backend/core/v8/db_init.py` migration.
2. **Boot Monolith:** 
   ```bash
   docker compose up -d --build
   ```
3. **Verify Resonance:** Use `python verify_v8_master.py` to confirm all 5 cognitive stores are linked.

### 📱 4. Mobile Adaptive Telemetry (Pulse v4.1)
Deployment supports high-fidelity mobile monitoring via the `?profile=mobile` SSE hook. This enables:
- **Event Filtering:** Only critical mission pulses are dispatched.
- **zlib Compression:** Payloads are compressed for cellular efficiency.

---

## 🔐 5. Environmental Configuration Validation

```env
# ── Sovereign Monolith v9.8.1 ──
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/levidb
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687

# ── Cognitive Acceleration ──
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
OPENAI_API_KEY=sk-... 
```

> [!CAUTION]
> **Monolith Resource Limits:** Ensure the API container has at least 12GB of addressable memory to support complex 30-node DAG executions without OOM-kills.

---

© 2026 LEVI-AI SOVEREIGN HUB.
