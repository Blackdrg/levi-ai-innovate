## [14.0.0-Autonomous-SOVEREIGN] — 2026-04-07 (Production Graduation)
### **Production Hardening & System Stability**

- **[SECURITY]** EgressProxy: Deny-by-Default allowlist (Tavily/SerpAPI only).
- **[SECURITY]** SecurityHeadersMiddleware: CSP, HSTS, X-Frame-Options, X-System-Version.
- **[SECURITY]** Rate Limiting: Redis ZSET sliding window — active on all task endpoints.
- **[BREAKING]** Docker sandbox migrated to Rootless Unix Socket; TCP:2375 removed.
- **[BREAKING]** `MAX_CONCURRENT` hard-gated to **4** (Resource Safety). Tasks queued on overflow.
- **[LOGIC]** Evaluation Formula: S = (Model×0.6) + (Literal×0.4).
- **[FEAT]** Postgres WAL archiving: 5-minute intervals → `./vault/backups/wal`.
- **[FEAT]** `SnapshotOrchestrator`: Coordinated 4-store backup (Postgres, Neo4j, Redis, FAISS).
- **[FEAT]** `restore_drill.py`: Automated RTO < 300s verification.
- **[STUB]** `LearningLoop`: Performance patterns (S > 0.85) → `training_corpus`. 
- **[FEAT]** `GET /api/v1/learning/metrics`: Performance monitoring dashboard.
- **[PREVIEW]** DCN v2.0: HMAC-SHA256 event synchronization via Redis Streams.
- **[DCN]** Coordinator-only wave enqueue enforced (RBAC for distributed tasks).
- **[DCN]** Resource-based task stealing across distributed nodes.

---

## [14.0.0-RC1] — 2026-04-06 (Release Candidate)
### **Distributed Stack Architecture**
- **Architecture**: Service-oriented Distributed Stack (FastAPI, Redis, Postgres, Neo4j, Celery).
- **Evaluation**: Rule-based validation integrated into parallel agent consensus.
- **Versioning**: Integrated `X-System-Version` middleware.
- **DCN Protocol**: HMAC-SHA256 inter-node event synchronization.

---

## [13.1.0] — 2026-04-05 (Stabilization)
- Orchestration resilience: Throttling and Circuit Breaker logic.
- HMAC-signed event synchronization protocol.
- FAISS Optimization: `efSearch=64`, `efConstruction=200` (sub-30ms context recall).

---

## [13.0.0] — 2026-04-05 (Technical Milestone)
- Storage Localization: Unified project drive migration.
- Local Inference: Integration of Ollama for local model hosting.
- Orchestrator Core + 4-Tier Memory Manager integration.
- React-based Task Controller with real-time SSE telemetry.

---

## [9.8.1] — 2026-04-04 (Architecture Pivot)
- Unified modular system architecture.
- PII Masking and NER-based data boundaries.
- Dynamic DAG Planning and Parallel Task Execution.

---

## [8.0.0] — 2026-04-03 (Initial Core)
- Orchestrator-driven architectural transition.
- Quad-Persistence Memory Layer implementation.
- Functional Agent Registry integration.
