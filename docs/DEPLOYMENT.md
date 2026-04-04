# 🚢 LEVI-AI Sovereign Monolith Deployment Architecture (v9.8.1)

> [!IMPORTANT]
> **LeviBrain v9.8.1 "Sovereign Monolith" Specification**
> LEVI-AI has transitioned to a High-Fidelity **Unified Cognitive Monolith**. Deployment centers on a high-performance **API Container** (Orchestration + Brain) and a **Generative Worker** (Multi-Pass Reasoning), backed by the **Sovereign Service Fabric** (Postgres, Redis, Kafka, FAISS, Firestore, Neo4j).

---

## 🏗️ 1. Infrastructure Topology (v8.11.1)

The v8.11.1 Monolith uses a topological wave execution model, requiring a distributed service fabric for cognitive pulse and relational memory.

```mermaid
graph TD
    LB[Sovereign Load Balancer] --> HTTPS
    HTTPS --> Web[React / SPA Frontend]
    HTTPS --> V8[LeviBrain v8 API Monolith]
    
    %% Service Fabric
    V8 -->|Mission Logs| Postgres[(Postgres: Identity & Audit)]
    V8 -->|Context State| Redis[(Redis: Pulse & Cache)]
    V8 -->|Events| Kafka{Kafka: Telemetry Bus}
    V8 -->|Relational| Neo4j[(Neo4j: Knowledge Graph)]
    V8 -->|Vector| FAISS[[FAISS: Semantic Memory]]
    
    Kafka --> Worker[Monolith Generative Worker]
    Worker --> V8
    Worker -->|Episodic| Firestore[(Firestore: Interactions)]
```

---

## ⚙️ 2. Hardware Matrix Recommendations (v8.11.1)

LEVI-AI v9.8.1 requires coherent RAM for the sentence-transformer embeddings and the 8-step pipeline state.

| Node Type | Minimum Spec | Recommended Spec | Primary Role |
|-----------|--------------|------------------|--------------|
| **v8 API Monolith** | 4 vCPU, 8GB RAM | 8 vCPU, 16GB RAM | 8-Step Pipeline, Perception, Planning, and SSE Neural Pulse. |
| **Monolith Worker** | 4 vCPU, 8GB RAM | 16 vCPU, 32GB RAM | Multi-pass reasoning, Swarm Execution, and Trait Distillation. |
| **Sovereign Event Bus** | 2 vCPU, 2GB RAM | 4 vCPU, 4GB RAM | Kafka/Zookeeper for cognitive pulse and telemetry distribution. |
| **Knowledge Graph** | 2 vCPU, 4GB RAM | 4 vCPU, 8GB RAM | Neo4j cluster for research artifact mapping. |
| **Context Cache** | 1GB RAM | 4GB RAM Redis | Real-time state, Blackboard sync, and wave execution locking. |

---

## ☁️ 3. Deployment & Orchestration

### Multi-Container Graduation (Docker Compose)
The recommended production deployment is via the unified `docker-compose.yml`:
1. **Initialize Persistence:** Run the `backend/core/v8/db_init.py` migration script.
2. **Boot the Monolith:** 
   ```bash
   docker-compose up -d --build
   ```
3. **Verify Health:** Use `scripts/verify_v8_master.py` to ensure all 6 stores are online.

---

## 🔐 4. Environmental Configuration Validation

Ensure your `.env` contains the v8.11.1 Sovereign URI set:

```env
# ── Sovereign Monolith v9.8.1 ──
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/levidb
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
NEO4J_URI=bolt://neo4j:7687

# ── Cognitive Acceleration ──
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
OPENAI_API_KEY=sk-... 
```

> [!CAUTION]
> **v9.8.1 Survival Scores:** Memories with a Survival Score < 0.5 are purged after 90 days. Ensure periodic backups of the **FAISS Index** and **Postgres Audit Logs** to prevent identity drift.

---

© 2026 LEVI-AI SOVEREIGN HUB.
