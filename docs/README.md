# LEVI-AI Documentation

This directory contains the project-owned technical and operational documentation for the current LEVI-AI runtime.

## Current Status

As of 2026-04-08:

- The designated workflow is `Gateway -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`.
- The targeted production wiring suite is passing with `19 passed`.
- Health, readiness, workflow introspection, tracing, metrics, and Kubernetes rollout files are present in the active runtime.
- Broad live load validation, real infra chaos drills, and wider feature smoke coverage are still not fully proven.

## Key Documents

| Document | Purpose |
| :--- | :--- |
| `../README.md` | Main project overview and exact current status. |
| `PRODUCTION_RUNBOOK.md` | Operational boot, health, readiness, and incident-response guidance. |
| `DEPLOYMENT.md` | Deployment topology, Kubernetes rollout surfaces, and CI validation notes. |
| `../SYSTEM_MANIFEST.md` | Current system component manifest and runtime surfaces. |
| `../CHANGELOG.md` | Root release and hardening changelog. |
| `TODO.md` | Remaining work before full production proof. |
| `SECURITY.md` | Security controls and related references. |
| `INTEGRATION.md` | Integration contracts and protocol references. |
| `DIAGNOSTICS_MASTER.md` | Diagnostics and observability references. |

## Notes

- Prefer the root `README.md` and root `CHANGELOG.md` as the canonical top-level status documents.
- Historical documents in this folder may describe planned or preview capabilities; they should not be read as proof that every capability is fully production-validated.
