# LEVI-AI Production Runbook

This runbook reflects the current runtime behavior in the repository as of 2026-04-08.

## Boot Order

Start dependencies in this order:

1. Redis
2. Postgres
3. Neo4j
4. Ollama
5. FastAPI gateway

The gateway entrypoint is `backend/api/main.py`. A compatibility import surface is also exposed at `backend/main.py`.

## Health and Readiness

Use these endpoints during operations:

- `GET /health` or `GET /api/v1/health`: runtime pulse, version, environment, model assignments, and startup checks.
- `GET /ready` or `GET /api/v1/ready`: readiness probe for Docker and Kubernetes. This checks Redis, Postgres resonance, and startup production-readiness conditions.
- `GET /metrics`: Prometheus metrics endpoint.
- `GET /api/v1/telemetry/workflow`: designated workflow manifest and contract-level telemetry surface.

`/ready` only returns `ready` when:

- Redis is reachable.
- Postgres resonance verification succeeds.
- Startup checks report `ready_for_production=true`.

## Startup Checks

The gateway startup contract currently verifies:

- `JWT_SECRET`
- `INTERNAL_SERVICE_KEY`
- `CORS_ORIGINS`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `REDIS_URL`

In `production`, missing secure values are surfaced as readiness warnings.

## Backpressure and Budget Enforcement

The executor now applies:

- VRAM-aware throttling
- CPU-aware throttling
- RAM-aware throttling
- queue-depth-aware throttling
- mission `token_limit` enforcement
- mission `tool_call_limit` enforcement

If the system degrades under pressure, the executor can reduce concurrency or fall back to safer execution behavior.

## Deployment Checks

Kubernetes rollout files live under `backend/deployment/k8s/`:

- `deployment.yaml`
- `hpa.yaml`
- `pdb.yaml`

Current runtime assumptions in those manifests:

- `ENVIRONMENT=production`
- readiness probe uses `/ready`
- liveness probe uses `/health`
- startup probe uses `/ready`

## CI Validation

The repository test workflow currently runs the targeted stability and workflow suite plus Kubernetes manifest validation:

```bash
pytest backend/tests/test_gateway_workflow_manifest.py backend/tests/test_pipeline_workflow.py backend/tests/test_stability_hardening.py backend/tests/test_reasoning_core_upgrade.py backend/tests/test_state_and_replay_upgrade.py --tb=short
```

The broader local verification that was recently used for status updates also includes:

```bash
.\.venv\Scripts\python.exe -m pytest backend/tests/test_gateway_workflow_manifest.py backend/tests/test_pipeline_workflow.py backend/tests/test_production_wiring.py backend/tests/test_stability_hardening.py backend/tests/test_reasoning_core_upgrade.py backend/tests/test_state_and_replay_upgrade.py -q
```

Verified result on 2026-04-08:

- `19 passed`

## Known Gaps

This repository is better wired for production, but these areas still need more proof before claiming full real-world readiness:

- high-concurrency live load runs
- real dependency chaos drills
- broader route-by-route smoke validation
