# LEVI-AI System Manifest

This manifest summarizes the currently active and documented runtime surfaces in the repository as of 2026-04-08.

## Designated Workflow

`Gateway -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`

The workflow contract is implemented in `backend/core/workflow_contract.py` and is inspectable at `GET /api/v1/telemetry/workflow`.

## Core Runtime Services

| Service | Path | Current role |
| :--- | :--- | :--- |
| FastAPI gateway | `backend/api/main.py` | Primary HTTP entrypoint, middleware, health, readiness, tracing, metrics, and router registration. |
| Compatibility gateway | `backend/main.py` | Backward-compatible import surface exposing `app` and legacy helpers. |
| Orchestrator | `backend/core/orchestrator.py` | Mission lifecycle coordination. |
| Goal engine | `backend/core/goal_engine.py` | Converts user input into structured objectives. |
| Planner | `backend/core/planner.py` | Builds DAG plans and supports compatibility helpers used by memory and learning paths. |
| Reasoning core | `backend/core/brain.py` | Performs reasoning pass, critique, refinement, and policy bridging. |
| Executor | `backend/core/executor/__init__.py` | Runs DAG waves, retries, backpressure, and budget enforcement. |
| Execution guardrails | `backend/core/execution_guardrails.py` | Shared guardrail logic for budgets, sandboxing, and enforcement boundaries. |
| Workflow contract | `backend/core/workflow_contract.py` | Validates and reports designated workflow integrity. |

## Persistence and State

| Component | Path | Current role |
| :--- | :--- | :--- |
| Redis | `backend/db/redis.py` | Runtime state, queues, cache, rate limiting, readiness dependency. |
| Postgres | `backend/db/postgres_db.py` | Resonance verification and persistent data surfaces. |
| Neo4j | `backend/db/neo4j_client.py` | Relational memory and graph surfaces. |
| Vector store | `backend/db/vector_store.py` | Semantic retrieval plus compatibility adapter for legacy flows. |
| Task graph | `backend/core/task_graph.py` | DAG structure, validation, and depth reporting. |

## Runtime Guarantees Added in the Current Pass

- stricter DAG validation
- bounded retries with backoff behavior
- sandbox and tool-boundary enforcement
- mission token-budget enforcement
- mission tool-call-budget enforcement
- multi-signal backpressure using VRAM, CPU, RAM, and queue depth
- startup readiness contract reporting

## Observability Surfaces

| Surface | Path | Current role |
| :--- | :--- | :--- |
| Metrics hub | `backend/utils/metrics.py` | Prometheus metrics export. |
| Tracing setup | `backend/utils/tracing.py` | OpenTelemetry setup with non-blocking runtime posture. |
| Evaluation tracing | `backend/evaluation/tracing.py` | Request and reasoning trace propagation. |
| Telemetry API | `backend/api/v8/telemetry.py` | SSE telemetry, swarm status, and workflow manifest endpoint. |
| Startup checks | `backend/utils/startup.py` | Production-readiness checks surfaced through `/health` and `/ready`. |

## Deployment Surfaces

| Surface | Path | Current role |
| :--- | :--- | :--- |
| Kubernetes deployment | `backend/deployment/k8s/deployment.yaml` | Rolling deployment, startup/liveness/readiness probes, graceful termination. |
| Kubernetes HPA | `backend/deployment/k8s/hpa.yaml` | CPU and memory autoscaling behavior. |
| Kubernetes PDB | `backend/deployment/k8s/pdb.yaml` | Disruption protection. |
| CI workflow | `.github/workflows/test.yml` | Targeted workflow/stability tests plus manifest validation. |

## Verified Status

The targeted production wiring suite used for the current status report passed on 2026-04-08 with `19 passed`.
