# LEVI-AI Repo Status

Snapshot updated for the v14.1.0-Autonomous-SOVEREIGN release on 2026-04-10.

## Runtime

- Active gateway entrypoint: `backend/api/main.py`
- Compatibility import surface: `backend/main.py`
- Active startup script: `backend/entrypoint.sh`
- Active container port: `8080` inside the container, mapped to `8000` on Docker Compose
- Designated workflow: `Gateway -> Fast-Path -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`

## Current Hardening State

- **Graduated (v14.1)**: **Fast-Path Routing** ultra-low latency bypass for common intents (< 2s response).
- **Graduated (v14.1)**: **3-Tier Semantic Caching** (Response-Exact, Vector-Similar, Strategy-Template) for O(1) recall.
- **Graduated (v14.1)**: **DCN Stability**: Leader Election (Term-based) and P2P State Reconciliation (Anti-Entropy) active.
- **Graduated (v14.1)**: **Security Anomaly Detector**: Mandatory pre-perception payload filtering gate.
- **Graduated (v14.1)**: **Agent Resource Budgeting**: Per-node token and call limits enforced by `ExecutionBudgetTracker`.
- **Graduated (v14.1)**: **Memory Hygiene**: Automated 24h resonance-based pruning and cold-storage archiving.
- **Graduated (v14.1)**: **Cognitive Billing**: 3-tier pricing (Free/Pro/Enterprise) with credit-based quota enforcement.
- **Audit-Ready**: SSRF Allowlist Wall implemented and explicitly denies non-approved outbound requests.
- **Audit-Ready**: Strict Security Headers (CSP, HSTS, X-Frame-Options) injected across all production endpoints.
- **Audit-Ready**: Sliding Window Rate Limiter guards endpoints by assigning strict Tiered API quotas.
- Structured logs include `trace_id`, `mission_id`, `node_id`, `duration_ms`, and `status`.
- Prometheus auto-scaling exposes Kubernetes metrics via `scripts/auto_scaler.py`.

## Verification

- Hardening Completion Suite: `42 passed` (including Fast-Path and DCN Resilience).
- Smoke Suite: `100% success` across all v14.1 routers.
- Security Persistence: `100% coverage` for RLS, PII masking, and SSRF walls.

## Recently Closed
- **v14.1 Proactive Optimization**: Fast-path routing and 3-tier caching implemented for zero-compute recall.
- **Swarm Integrity**: Sticky Leader Election and P2P reconciliation loop finalized in `main.py`.
- **Resilience**: Priority Queues and Dead-Letter Queue (DLQ) configured for resilient task execution.
- **Security**: Pre-perception Anomaly Detector gate and agent-level resource budgeting integrated.
- **Hygiene**: 24h automated memory resonance pruning cycle active.

## Key Docs

- `README.md`
- `SYSTEM_MANIFEST.md`
- `SECURITY_AUDIT_SCOPE.md`
- `CHANGELOG.md`
- `scripts/deploy/verify_production.ps1` (10-Step Launch Sequence)
