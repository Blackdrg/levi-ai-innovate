# Absolute Monolith Hardening: v13.0.0 Production Graduation

This plan outlines the technical implementation for fixing 28 identified critical, high, and medium-level issues to graduate LEVI-AI to a production-ready Sovereign OS.

## User Review Required

> [!IMPORTANT]
> This is a massive overhaul of the system's core. Some changes (including Multi-tenant isolation and HNSW migration) will require database migrations and potential re-indexing of existing data.

> [!WARNING]
> **Code Sandboxing** requires Docker to be running on the host machine to provide real isolation. If Docker is not available, we will implement the strictest possible local process isolation as a fallback.

> [!CAUTION]
> **Multi-tenant isolation** will change how data is queried. Legacy data without a `tenant_id` will be inaccessible unless migration scripts are run.

## Proposed Changes

The implementation is divided into four main thrusts: **Security**, **Architecture**, **Reliability**, and **Intelligence**.

---

### Phase 1: Security Hardening (Shield & Sandbox)

#### [MODIFY] [generation.py](file:///d:/LEVI-AI/backend/engines/chat/generation.py)
- Integrate `PromptSanitizer` to prevent injection.
- Implement instruction-boundary enforcement (e.g., `<INST>` tags).

#### [MODIFY] [python_repl_agent.py](file:///d:/LEVI-AI/backend/agents/python_repl_agent.py)
- Replace `exec` with a `DockerSandbox` executor.
- Define resource limits (CPU, Memory, IO).

#### [NEW] [sanitizer.py](file:///d:/LEVI-AI/backend/utils/sanitizer.py)
- regex-based and LLM-based (fast-local) input sanitization for adversarial patterns.

#### [NEW] [secret_manager.py](file:///d:/LEVI-AI/backend/config/secret_manager.py)
- Abstract secret access with rotation logic and TTL support.

---

### Phase 2: Architectural Integrity (Multi-tenancy & Ontology)

#### [MODIFY] [models.py](file:///d:/LEVI-AI/backend/db/models.py)
- Update models to support Row Level Security (RLS) hooks.
- Implement `system_audit` cryptographic chaining.

#### [MODIFY] [vector_store.py](file:///d:/LEVI-AI/backend/db/vector_store.py)
- Add `model_metadata` header to HNSW index file.
- Implement tenant-scoped partitioning for vector searches.

#### [NEW] [ontology.py](file:///d:/LEVI-AI/backend/db/ontology.py)
- Define Pydantic models for Neo4j Entity-Relation triplets with validation constraints.

#### [MODIFY] [base.py](file:///d:/LEVI-AI/backend/agents/base.py)
- Enforce Pydantic structured output contracts for all agents.

---

### Phase 3: Reliability & Operations (CI/CD & Recovery)

#### [NEW] [deploy.yml](file:///d:/LEVI-AI/.github/workflows/deploy.yml)
- Full CI/CD pipeline: Build, Tag, K8s Deploy, Canary rollout.

#### [NEW] [backup_policy.py](file:///d:/LEVI-AI/backend/scripts/backup_policy.py)
- Automated backup orchestration for Postgres (pg_dump), Neo4j (dump), and HNSW.

#### [MODIFY] [celery_app.py](file:///d:/LEVI-AI/backend/celery_app.py)
- Implement mission cancellation protocol via Redis signals.

---

### Phase 4: Intelligence & Cost (Fidelity & CUs)

#### [MODIFY] [fidelity.py](file:///d:/LEVI-AI/backend/evaluation/fidelity.py)
- Formally define Fidelity Score S as a weighted aggregation of 14 agent outputs.

#### [NEW] [billing.py](file:///d:/LEVI-AI/backend/services/billing.py)
- Implement Cognitive Unit (CU) formula calculation and per-user ledger.

#### [MODIFY] [planner.py](file:///d:/LEVI-AI/backend/engines/brain/planner.py)
- Add DAG cycle detection algorithm.

## Open Questions

- **Docker Availability**: Can I assume Docker is available for the sandbox?
- **Secrets Management**: Should I use a local mock for Vault or is there a specific provider preferred?
- **Fidelity Weights**: Are there preferred weights for the 14 agents in the S calculation?

## Verification Plan

### Automated Tests
- `pytest tests/security/test_injection.py`
- `pytest tests/architecture/test_tenancy.py`
- `pytest tests/agents/test_outputs.py`

### Manual Verification
- Trigger a mission and attempt to cancel it mid-stream via the API.
- Verify vector index corruption check by manually changing the model name in metadata.
