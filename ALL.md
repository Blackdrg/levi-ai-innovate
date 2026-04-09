# LEVI-AI Repo Status

Snapshot updated for the current hardening pass on 2026-04-09.

## Runtime

- Active gateway entrypoint: `backend/api/main.py`
- Compatibility import surface: `backend/main.py`
- Active startup script: `backend/entrypoint.sh`
- Active container port: `8080` inside the container, mapped to `8000` on Docker Compose
- Designated workflow: `Gateway -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`

## Current Hardening State

- **Audit-Ready**: SSRF Allowlist Wall implemented and explicitly denies non-approved outbound domain requests.
- **Audit-Ready**: Strict Security Headers (CSP, HSTS, X-Frame-Options) injected across all production endpoints via middleware.
- **Audit-Ready**: Sliding Window Rate Limiter guards endpoints by assigning strict Tiered API quotas.
- Integration tests written and actively enforce SSRF bounds, rate limits, and security headers.
- `/health` performs real Redis, Postgres, and `Ollama /api/tags` checks
- `/ready` gates on dependency reachability plus startup production-readiness checks
- Structured logs include `trace_id`, `mission_id`, `node_id`, `duration_ms`, and `status`
- RBAC negative-path tests cover missing token, expired token, and wrong-role token
- Mission idempotency has a concurrent regression test
- Executor compensation is exercised in tests
- Active backend startup now runs Alembic migrations
- Graceful shutdown drains tracked background mission tasks before exit, with Orchestrator `teardown_gracefully` interrupting and flushing all live executing tasks.
- Local live chaos script exists at `scripts/chaos/run_live_chaos.py`
- Focused k6 mission load script exists at `tests/load/missions_k6.js`
- Prometheus auto-scaling exposes Kubernetes metrics via `scripts/auto_scaler.py`
- Python API SDK available at `shared/sdk/python/levi_client.py`

## Verification

- Workflow and stability suite: `19 passed`
- Additional hardening suite: `9 passed`
- Shutdown, auth, and idempotency tranche: `6 passed`
- Chaos Mesh and Circuit Breakers (GPU/Neo4j Failure Survivability): `8 passed`

## Still Open

- wider route-by-route smoke coverage
- Penetration test resolution buffering

## Recently Closed

- Full 4-Phase System Maturity Plan executed.
- Added agent reflexive-retry loops for internal self-correction.
- Dynamic Token-Optimization down-routing via complexity float mapping.
- Passive graph-template decay using fidelity performance culling.
- Front-end integration for Replay visualization.

## Key Docs

- `README.md`
- `SYSTEM_MANIFEST.md`
- `docs/PRODUCTION_RUNBOOK.md`
- `CHANGELOG.md`
- `scripts/deploy/verify_production.ps1` (10-Step Launch Sequence)
