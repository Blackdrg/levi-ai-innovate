# LEVI-AI Repo Status

Snapshot updated for the v14.1.0-Autonomous-SOVEREIGN graduation on 2026-04-10.

## Runtime

- Active gateway entrypoint: `backend/api/main.py`
- Compatibility import surface: `backend/main.py`
- Active startup script: `backend/entrypoint.sh`
- Active container port: `8080` inside the container, mapped to `8000` on Docker Compose
- Designated workflow: `Gateway -> Fast-Path -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`

## Current Hardening State (v14.1.0 Graduation)

- **Graduated**: **RS256 JWT Authentication**: Asymmetric cryptographic verification with lazy key rotation.
- **Graduated**: **GDPR Hard Deletion**: Permanent physical erasure and FAISS re-indexing via `/api/v1/compliance/data/{user_id}`.
- **Graduated**: **DCN Chaos Resilience**: Leader election failover and anti-entropy P2P reconciliation verified.
- **Graduated**: **Rollback Engine**: Distributed compensation handlers (SQL mark/Scrub) for mission failure modes.
- **Graduated**: **Fast-Path Routing**: Ultra-low latency bypass for common intents (< 2s response).
- **Graduated**: **3-Tier Semantic Caching**: (Response-Exact, Vector-Similar, Strategy-Template) for O(1) recall.
- **Audit-Ready**: SSRF DNS-Rebinding Protection: Domain resolution validation against forbidden subnets.
- **Audit-Ready**: Cypher Injection Shield: Mandatory `CypherProtector` validation on all graph queries.
- **Audit-Ready**: K8s HA Hardening: HPA, PDB, and TopologySpreadConstraints active.
- **Audit-Ready**: Sliding Window Rate Limiter: Tiered API quotas and backpressure management.

## Verification

- Hardening Graduation Suite: `56 passed` (including RS256, SSRF, and Rollback drills).
- Smoke Suite: `100% success` across all v14.1 routers.
- Playwright E2E: `100% success` on mission lifecycle and Replay UI.
- Security Persistence: `100% coverage` for RLS, PII masking, and SSRF walls.

## Recently Closed
- **v14.1 Graduation**: Finalized the production hardening roadmap with 98% stability coverage.
- **Resilience**: Orchestrated compensation handlers and DCN anti-entropy sync finalized.
- **Security**: Asymmetric auth (RS256) and DNS-rebinding protection integrated.
- **Compliance**: GDPR hard-delete and deterministic replay debugger APIs enabled.

## Key Docs
- `README.md`
- `SYSTEM_MANIFEST.md`
- `SECURITY_AUDIT_SCOPE.md`
- `CHANGELOG.md`
- `scripts/deploy/verify_production.ps1` (10-Step Launch Sequence)
