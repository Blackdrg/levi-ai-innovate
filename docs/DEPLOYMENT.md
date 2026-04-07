# 🚢 LEVI-AI: Deployment Guide (v13.1.0-Hardened-PROD)

> **LEVI-AI v13.1.0-Hardened-PROD Production Specification**
> This architecture coordinates five primary services (FastAPI, Redis, Postgres, Neo4j, Celery) for absolute data residency and high-performance mission orchestration at local-first sovereign standard.

---

## 1. Service Topology (Hardened)

```mermaid
graph TD
    User((User / Client)) -->|HTTPS / SSE| Gateway[FastAPI Gateway]

    subgraph "Core Stack"
        Gateway -->|Identity & Audit| Postgres[(Postgres: Episodic Memory)]
        Gateway -->|Task Queue & Blackboard| Redis[(Redis: Working Memory)]
        Gateway -->|Relational Graph| Neo4j[(Neo4j: Knowledge Graph)]
        Gateway -->|Semantic Search| FAISS[[FAISS: Semantic Memory]]
        Gateway -->|Local Inference| Ollama[Ollama: Inference Layer]
    end
    
    subgraph "Background Layer"
        Redis --> Worker[Celery: Background Workers]
        Worker --> Postgres
        Worker --> Neo4j
    end
    
    subgraph "Distributed Preview (DCN v2.0)"
        Gateway -->|HMAC Pulse| GossipStream[(Redis Stream: dcn:gossip)]
        GossipStream -->|Task Distribution| TaskQueue[(Redis: dcn:task_queue)]
    end
```

---

## 2. Hardware Matrix [UPDATED]

| Service | Minimum | Recommended | Primary Role |
| :--- | :--- | :--- | :--- |
| **API Gateway** | 4 vCPU, 8GB RAM | 8 vCPU, 16GB RAM | Orchestration & Mission Planning |
| **Persistence Hub**| 2 vCPU, 4GB RAM | 4 vCPU, 8GB RAM | Postgres & Neo4j data storage |
| **Memory Bus** | 1 vCPU, 2GB RAM | 2 vCPU, 4GB RAM | Redis Working Memory & Task Queue |
| **Inference Layer** | 12GB VRAM | **24GB VRAM** | Local LLM (llama3.1:8b, Semaphore: 4) |

### GPU Scaling Tiers
| Tier | Hardware | VRAM | Concurrency |
| :--- | :--- | :--- | :--- |
| Minimum | RTX 3090 / 4090 | 24 GB | **4 slots** |
| Production | 2x RTX 3090 / A6000 | 48 GB | 12 slots |
| Enterprise | A100 / H100 | 80 GB | 32+ slots |

> [!NOTE]
> `MAX_CONCURRENT = 4` is the RC1 **Safety-First** default. Exceeding this on 24GB hardware causes CUDA OOM. Tasks queue rather than fail when all slots are busy.

---

## 3. Boot Sequence [UPDATED]

### Step 1 — Environment Preparation
```env
# Core Identity
SOVEREIGN_VERSION=v13.1.0-Hardened-PROD
ENVIRONMENT=production

# Service Connectivity
DATABASE_URL=postgresql+asyncpg://leviuser:pass@postgres:5432/levidb
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Security (REQUIRED — generate your own)
DCN_SECRET=<64-char-hex>
AUDIT_CHAIN_SECRET=<64-char-hex>

# Sovereignty Defaults
CLOUD_FALLBACK_ENABLED=false
DISTRIBUTED_MODE=false
NODE_ROLE=coordinator
NODE_WEIGHT=4
```

### Step 2 — Launch Services
```bash
docker-compose up -d --build
```

### Step 3 — Pull Inference Models
```bash
ollama pull llama3.1:8b
ollama pull phi3:mini
ollama pull nomic-embed-text
```

### Step 4 — Run Graduation Audit
```bash
pytest tests/production_readiness_suite.py -v
# Expected: 28 passed
```

### Step 5 — Resonance Check
Open the **Evolution Dashboard** at `http://localhost:3000` and observe:
- 🟢 Pulse: Active
- 🟢 DCN Heartbeat streaming
- 🟢 Learning Metrics populated

---

## 4. Disaster Recovery Boot [NEW]

If restoring from a backup event:

```bash
# 1. Restore all stores from latest snapshot
python -m backend.scripts.restore_drill

# 2. Verify RTO compliance (must complete in < 300s)
# 3. Re-run graduation audit to confirm integrity
pytest tests/production_readiness_suite.py -v
```

---

## 5. DCN Multi-Node Boot (Preview) [NEW]

> [!IMPORTANT]
> DCN multi-physical-server deployment is **Preview (Q3 2026)**. The following activates task distribution within a shared Redis environment only.

```env
# On Coordinator Node
NODE_ROLE=coordinator
NODE_WEIGHT=4
DISTRIBUTED_MODE=true
DCN_NODE_ID=node-alpha

# On Worker Node
NODE_ROLE=worker
NODE_WEIGHT=8
DISTRIBUTED_MODE=true
DCN_NODE_ID=node-beta
```

---

© 2026 LEVI-AI SOVEREIGN HUB — Deployment Specification v13.1.0-Hardened-PROD
