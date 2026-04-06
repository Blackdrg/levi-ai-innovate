# 🚢 LEVI-AI: Local-First Distributed Stack (v1.0.0-RC1)

> [!IMPORTANT]
> **LEVI-AI v1.0.0-RC1 Production Specification**
> LEVI-AI has transitioned to a **Local-First Distributed Stack**. This architecture coordinates five primary services (FastAPI, Redis, Postgres, Neo4j, and Celery) to ensure absolute data residency and high-performance mission orchestration.

---

## 🏗️ 1. Service Topology (v1.0.0-RC1)

The v1.0.0-RC1 stack uses a service-oriented model with a low-latency local fabric.

```mermaid
graph TD
    User((User/Client)) -->|HTTPS/SSE| Gateway[FastAPI Gateway]
    
    subgraph "Core Stack"
        Gateway -->|Identity & Audit| Postgres[(Postgres: Episodic Memory)]
        Gateway -->|Task Queue| Redis[(Redis: Working Memory)]
        Gateway -->|Relational Graph| Neo4j[(Neo4j: Knowledge Graph)]
        Gateway -->|Semantic Search| FAISS[[FAISS: Semantic Memory]]
        Gateway -->|Local Inference| Ollama[Ollama: Inference Layer]
    end
    
    subgraph "Background Layer"
        Redis --> Worker[Celery: Background Workers]
        Worker --> Postgres
        Worker --> Neo4j
    end
```

---

## ⚙️ 2. Hardware Matrix Recommendations

Optimized for the distributed stack with local inference.

| Service | Minimum Spec | Recommended Spec | Primary Role |
| :--- | :--- | :--- | :--- |
| **API Gateway** | 4 vCPU, 8GB RAM | 8 vCPU, 16GB RAM | Orchestration & Mission Planning. |
| **Persistence Hub**| 2 vCPU, 4GB RAM | 4 vCPU, 8GB RAM | Postgres & Neo4j data storage. |
| **Memory Bus** | 1 vCPU, 2GB RAM | 2 vCPU, 4GB RAM | Redis Working Memory & Task Queue. |
| **Inference Layer**| 12GB VRAM | 24GB VRAM | Local LLM Inference (llama3.1:8b). |

---

## ☁️ 3. Deployment & Boot Sequence

### Production Stack (Docker Compose)
The v1.0.0-RC1 deployment is managed via a unified compose file:
1. **Prepare Environment:** Configure `.env` with `DCN_SECRET` and `SOVEREIGN_VERSION`.
2. **Launch Services:**
   ```bash
   docker compose up -d --build
   ```
3. **Verify Health:** Use `pytest tests/v1_graduation_suite.py` to confirm all 28 audit points are verified.

---

## 🔐 4. Environmental Configuration Validation

```env
# ── LEVI-AI v1.0.0-RC1 ──
SOVEREIGN_VERSION=v1.0.0-RC1
ENVIRONMENT=production

# ── Service Connectivity ──
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/levidb
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687

# ── Sovereign Defaults ──
CLOUD_FALLBACK_ENABLED=false
DCN_SECRET=64_character_hex_signing_secret
```

---

© 2026 LEVI-AI SOVEREIGN HUB.
