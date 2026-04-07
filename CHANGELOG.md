## [1.0.0-RC1] — 2026-04-07 (Sovereign Graduation Complete)
### **Full Production Hardening — Absolute Monolith**

- **[SECURITY]** EgressProxy: Deny-by-Default allowlist (Tavily/SerpAPI only).
- **[SECURITY]** SecurityHeadersMiddleware: CSP, HSTS, X-Frame-Options, X-Sovereign-Version.
- **[SECURITY]** Rate Limiting: Redis ZSET sliding window — active on all mission endpoints.
- **[BREAKING]** Docker sandbox migrated to Rootless Unix Socket; TCP:2375 removed.
- **[BREAKING]** `MAX_CONCURRENT` hard-gated to **4** (GPU Safety). Tasks queued on overflow.
- **[LOGIC]** Fidelity Formula locked: S = LLM×0.6 + Rule×0.4.
- **[FEAT]** Postgres WAL archiving: 5-minute intervals → `./vault/backups/wal`.
- **[FEAT]** `SnapshotOrchestrator`: Coordinated 4-store backup (Postgres, Neo4j, Redis, FAISS).
- **[FEAT]** `restore_drill.py`: Automated RTO < 300s verification.
- **[STUB]** `LearningLoop`: S > 0.85 patterns → `training_corpus`. Weights NOT modified.
- **[FEAT]** `GET /api/v1/learning/metrics`: Evolution Dashboard metrics endpoint.
- **[PREVIEW]** DCN v2.0: HMAC-SHA256 gossip via Redis Streams. Target production: Q3 2026.
- **[DCN]** Coordinator-only wave enqueue enforced (RBAC for distributed tasks).
- **[DCN]** NODE_WEIGHT-based weighted task stealing across swarm nodes.

---

## [1.0.0-RC1] — 2026-04-06 (Initial Graduation Candidate)
### **Local-First Distributed Stack Graduation**
- **RC Certification**: 28-point graduation audit finalized.
- **Architectural Realism**: Service-oriented Distributed Stack (FastAPI, Redis, Postgres, Neo4j, Celery).
- **Deterministic Fidelity**: 40% rule-based validation integrated into Consensus protocol.
- **Global Versioning**: `X-Sovereign-Version` middleware and centralized RC1 branding.
- **DCN Gossip**: HMAC-SHA256 inter-node pulse for peer-to-peer telemetry sync.

---

## [13.1.0] — 2026-04-05 (Stabilization)
- Learning Loop resilience: throttling and Circuit Breaker logic.
- HMAC-signed Gossip Protocol deployed via Redis PubSub.
- HNSW: `efSearch=64`, `efConstruction=200` synchronized (sub-30ms recall).

---

## [13.0.0] — 2026-04-05 (Technical Graduation)
- Drive Localization: 100% D: drive migration.
- Local Inference: Ollama (llama3.1:8b) replacing cloud dependencies.
- BrainCoreController + 5-Tier Memory Manager integrated.
- React + Zustand Mission Controller with real-time SSE.

---

## [9.8.1] — 2026-04-04
- Unified v8 Monolith architecture.
- Sovereign Shield NER masking deployed.
- Dynamic DAG Planning Wave Executor implemented.

---

## [8.0.0] — 2026-04-03
- Brain-first architectural transition.
- 5-tier Resonant Memory Fabric deployed.
- Core Agent Swarm integrated.
