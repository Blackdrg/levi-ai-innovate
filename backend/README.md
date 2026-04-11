# LEVI-AI Backend Technical Manifest (v14.2)

The LEVI-AI backend is a high-performance cognitive gateway built on FastAPI. it orchestrates the mission lifecycle from intent classification to distributed host-agent execution.

## ⚙️ Architecture

- **FastAPI Gateway**: Entry point for all mobile, voice, and web clients.
- **Orchestrator Service**: The "State Authority" tracking mission progress.
- **Planner Service**: Decomposes user intent into a Sovereign Task Graph (DAG).
- **Executor Service**: Parallelizes agent waves across the DCN.
- **Memory Service**: Synchronizes the 4-tier cognitive memory layers.

### Request Lifecycle
`User Input → Auth & Shield → Orchestrator → DAG Planner → Reasoning Core → Graph Executor → Swarm → MCM Sync → Response`

## 📂 Folder Structure

```text
├── api/             # API Routers & Handlers
├── auth/            # Identity & RS256 JWT Logic
├── core/            # Central Engines (Orchestrator, Planner)
├── agents/          # Specialized Swarm Agents
├── db/              # Persistent Stores (Postgres, Neo4j)
├── memory/          # Cognitive Tiers (FAISS, Cache)
├── middleware/      # 4-Layer Security Stack
├── services/        # Third-party & MCM Logic
└── utils/           # Shared Utilities & Tracing
```

## 🛡️ Middleware Stack
1. **PrometheusMiddleware**: Tracks latency and CU costs at the edge.
2. **RateLimitMiddleware**: Tiered sliding window enforcement (Redis-backed).
3. **SSRFMiddleware**: Egress protection via precision CIDR blocking and pre-request DNS resolution.
4. **SovereignShieldMiddleware**: RBAC and asymmetric JWT verification.

## 🔌 API Examples

### POST `/api/v1/orchestrator/mission`
**Request Body**:
```json
{
  "objective": "Research the latest autonomous OS trends.",
  "mode": "autonomous",
  "fidelity_threshold": 0.85
}
```

**Response**:
```json
{
  "mission_id": "m_123456",
  "status": "CREATED",
  "est_latency": "15s",
  "cu_locked": 5.0
}
```

## 🧪 Error Handling
All errors use the `SovereignError` format with a remediation pulse:
```json
{
  "error_code": "LEVI_004_VRAM_REJECTION",
  "message": "Resource pressure high.",
  "remediation": "Switch to linear execution mode."
}
```
