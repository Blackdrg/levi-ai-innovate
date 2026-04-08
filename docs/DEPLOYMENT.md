# LEVI-AI Deployment Guide

This guide reflects the deployment surfaces that exist in the repository today.

## Active Runtime Topology

The current runtime centers on:

- FastAPI gateway
- Redis
- Postgres
- Neo4j
- Ollama
- Prometheus and Grafana integration surfaces

Some historical documents also mention other components and previews. Treat those as contextual, not as proof that every deployment mode is fully production-proven.

## Primary Entrypoints

- Gateway app: `backend/api/main.py`
- Compatibility import surface: `backend/main.py`
- Workflow manifest endpoint: `GET /api/v1/telemetry/workflow`
- Metrics endpoint: `GET /metrics`
- Liveness pulse: `GET /health`
- Readiness probe: `GET /ready`

## Kubernetes Manifests

Current Kubernetes files:

- `backend/deployment/k8s/deployment.yaml`
- `backend/deployment/k8s/hpa.yaml`
- `backend/deployment/k8s/pdb.yaml`

Current manifest behavior:

- Deployment replicas: `3`
- `minReadySeconds: 15`
- rolling update with `maxSurge: 1` and `maxUnavailable: 0`
- `startupProbe` uses `/ready`
- `readinessProbe` uses `/ready`
- `livenessProbe` uses `/health`
- `terminationGracePeriodSeconds: 30`
- HPA min replicas: `2`
- HPA max replicas: `10`
- HPA scales on CPU and memory utilization
- PDB requires `minAvailable: 2`

## Environment Expectations

At minimum, production deployment should set:

```env
ENVIRONMENT=production
DATABASE_URL=...
REDIS_URL=...
NEO4J_URI=...
OLLAMA_BASE_URL=...
JWT_SECRET=...
INTERNAL_SERVICE_KEY=...
CORS_ORIGINS=...
OTEL_EXPORTER_OTLP_ENDPOINT=...
```

The startup contract in `backend/utils/startup.py` reports readiness warnings when production-critical values are missing.

## Validation

GitHub Actions currently validates:

1. Targeted stability and workflow tests
2. Kubernetes YAML parsing for the active manifest set

Recent local status verification also included:

```bash
.\.venv\Scripts\python.exe -m pytest backend/tests/test_gateway_workflow_manifest.py backend/tests/test_pipeline_workflow.py backend/tests/test_production_wiring.py backend/tests/test_stability_hardening.py backend/tests/test_reasoning_core_upgrade.py backend/tests/test_state_and_replay_upgrade.py -q
```

Verified result on 2026-04-08:

- `19 passed`

## Honest Status

The repository is substantially more production-shaped than before, but these are still open:

- full live load characterization
- real dependency failure drills in deployed environments
- broader end-to-end route coverage
