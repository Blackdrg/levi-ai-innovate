# LEVI-AI System Evolution Log

This changelog is a documentation-friendly mirror of the root project changelog.

## [14.0.0-DOCS-REALITY-LOCK] - 2026-04-08

- Project docs updated to match the current runtime and validated test status.
- Designated workflow documented as `Gateway -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`.
- Operational docs updated for `/health`, `/ready`, `/metrics`, and `/api/v1/telemetry/workflow`.
- Deployment docs aligned with the current Kubernetes deployment, HPA, and PDB manifests.
- Current verified status recorded as `19 passed` for the targeted production wiring suite.
- Remaining gaps documented honestly: load, chaos, and wider smoke coverage are still in progress.

## Historical Note

Earlier markdown in this repository contains roadmap and graduation language from previous phases. Use the root `CHANGELOG.md` and root `README.md` for the most accurate current state.
