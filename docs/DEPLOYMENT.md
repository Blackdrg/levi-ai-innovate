# 🚢 LEVI-AI Sovereign Monolith Deployment Architecture

> [!IMPORTANT]
> **LeviBrain v8 "Cognitive Monolith" Specification**
> LEVI-AI has transitioned from a fragmented micro-service array to a **Unified Cognitive Monolith**. Deployment now centers on a high-fidelity **API Container** (Orchestration + Brain) and a **Generative Worker** (Multi-Pass Reasoning), backed by the **Sovereign Multi-Store** (Postgres, Redis, Kafka, Mongo).

---

## 🏗️ 1. Infrastructure Topology (v8)

The v8 Monolith uses a topological wave execution model, requiring a robust event bus (Kafka) for multi-brain synchronization.

```mermaid
graph TD
    LB[Sovereign Load Balancer] --> HTTPS
    HTTPS --> Web[Vite / SPA Frontend]
    HTTPS --> V8[LeviBrain v8 API Monolith]
    
    V8 -->|Mission Logs| Postgres[(Sovereign Mission Postgres)]
    V8 -->|Context State| Redis[(Sovereign Context Redis)]
    V8 -->|Trait Pulses| Kafka{Sovereign Event Bus}
    
    Kafka --> Worker[Monolith Generative Worker]
    Worker --> V8
    Worker -->|Semantic Vault| Mongo[(Semantic Vault Mongo)]
```

## ⚙️ 2. Hardware Matrix Recommendations (v8)

LEVI-AI v8 requires coherent RAM for the sentence-transformer embeddings and the 8-step pipeline state.

| Node Type | Minimum Spec | Recommended Spec | Primary Role |
|-----------|--------------|------------------|--------------|
| **v8 API Monolith** | 2 vCPU, 4GB RAM | 4 vCPU, 16GB RAM | 8-Step Pipeline, Perception, Planning, and API SSE Streaming. |
| **Monolith Worker** | 4 vCPU, 8GB RAM | 8 vCPU, 32GB RAM | Multi-pass reasoning, Image/Video generation, and Trait Distillation. |
| **Sovereign Event Bus** | 1 vCPU, 1GB RAM | 2 vCPU, 2GB RAM | Kafka/Zookeeper for cognitive pulse distribution. |
| **Context Cache** | 256MB RAM | 2GB RAM Redis | Real-time state and wave execution locking. |

---

## ☁️ 3. Deployment & Orchestration

### Multi-Container Graduation (Docker Compose)
The recommended production deployment for the v8 Monolith is via the unified `docker-compose.yml`:
1. **Initialize Persistence:** Run the `backend/core/v8/db_init.py` migration script.
2. **Boot the Monolith:** 
   ```bash
   docker-compose up -d --build
   ```
3. **Verify Health:** Use `scripts/verify_v8_infra.py` to ensure all 4 stores are online.

### GitHub Actions: Sovereign Graduate Pipeline
Deployment is automated via [sovereign-graduate.yml](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/.github/workflows/sovereign-graduate.yml):
- **Verify:** Runs `test_v8_core.py` on every push.
- **Deploy:** Builds and pushes the `sovereign-monolith:v8` image to your registry.

---

## 🔐 4. Environmental Configuration Validation

Ensure your `.env` contains the v8 Sovereign URI set:

```env
# ── Sovereign Monolith v8 ──
DATABASE_URL=postgresql://user:pass@postgres:5432/levidb
REDIS_URL=redis://redis:6379/0
KAFKA_URL=kafka:29092
MONGO_URL=mongodb://mongo:27017

# ── Cognitive Acceleration ──
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
OPENAI_API_KEY=sk-...  # For Identity DALL-E/GPT-4o fallback
```

> [!CAUTION]
> **v8 Importance Decay:** Memories with significance < 0.5 are purged periodically. Ensure your **Semantic Vault (Mongo)** has daily backups to prevent accidental loss of distiled traits.
