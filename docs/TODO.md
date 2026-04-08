# LEVI-AI Remaining Work

This file tracks the honest remaining work after the current hardening and documentation pass.

## Completed and Verified

- Designated pipeline wiring is connected end-to-end.
- Workflow contract reporting exists.
- Reasoning, executor, and memory-related hardening tests are passing.
- Health, readiness, tracing, metrics, Kubernetes rollout files, and CI validation are in place.
- Targeted local verification passed with `19 passed` on 2026-04-08.

## Still Needed Before Full Production Proof

- Run real load campaigns across 100, 500, and 1000 concurrent missions.
- Run long-DAG tests with depth greater than 10 under realistic dependency pressure.
- Run mixed-workload tests covering chat, research, and code flows together.
- Execute chaos drills against real Redis failure, Neo4j lag, agent timeout, and GPU overload behavior.
- Expand smoke coverage across more API routes and feature surfaces.
- Verify alert thresholds under stress, not just configuration presence.
- Validate replay determinism and memory consistency under multi-service failure and delayed sync conditions.

## Status

Current status is best described as:

- design wiring: complete
- targeted integration and hardening: verified
- full production proof under stress: still in progress
