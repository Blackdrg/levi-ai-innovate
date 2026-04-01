# LEVI-AI Operations Runbook

> **Version**: v6.8.5 — Sovereign Monolith Hardened 🏗️
> **Last Updated**: 2026-04-01  
> **Architecture**: Sovereign Monolith (FastAPI + Llama-3-8B + FAISS + GCS FUSE + Redis)

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Sovereign Monolith (Production)](#sovereign-monolith-production)
3. [CI/CD & Deployment](#cicd--deployment)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Health & Monitoring signals](#health--monitoring-signals)
6. [Common Operational Procedures](#common-operational-procedures)
7. [Troubleshooting](#troubleshooting)

---

## System Architecture

```
User (Web/Mobile)
    │
    ▼
[Cloud Run: levi-monolith]  ← Unified 8Gi Sovereign Processing 🚀
    │
    ├── [Llama-3-8B GGUF]   ← PROPRIETARY: Local reasoning engine
    ├── [GCS FUSE Mount]     ← PERSISTENCE: /mnt/vector_db (FAISS) 🧠
    ├── [Redis]              ← REAL-TIME: SSE Pulse, Session Cache, Rate Limits
    ├── [Firestore]          ← COLD STORAGE: Facts, Persona Traits, Analytics
    └── [Groq API]           ← FALLBACK: High-complexity reasoning
    │
    ▼
[Monolith Scheduler]         ← Background: Distillation, GC, Pulse Sync
```

---

## Sovereign Monolith (Production)

### Provisioning Requirements
- **Memory**: **8Gi** (Required for in-memory model + Vector Matrix).
- **CPU**: **4 vCPU** (Optimal for reasoning TPS).
- **Storage**: GCS Bucket mounted at `/mnt/vector_db` via **FUSE**.
- **Concurrency**: `MAX_LOCAL_CONCURRENCY=2` (Per instance).

### Deployment Action
All deployments are handled via GitHub Actions:
```bash
# Push to main triggers deploy_production.yml
# Verifies Sovereign Engine health before shifting traffic.
```

---

## CI/CD & Deployment

The GitHub Actions workflow (`.github/workflows/`) runs on every push to `main`:

1. **Lint** — `flake8` / `ruff`
2. **Test** — `pytest backend/tests/ -v --tb=short`
3. **Build** — `docker build .`
4. **Deploy** — Push image to registry, rolling restart on Cloud Run

### Running Tests Locally

```bash
# Full test suite
python -m pytest backend/tests/ -v --tb=short
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key |
| `GROQ_API_KEY` | ✅ | Primary LLM provider |
| `FIREBASE_PROJECT_ID` | ✅ | Firebase project name |
| `REDIS_URL` | ✅ | Redis connection URL |
| `ENVIRONMENT` | ✅ | `production` or `development` |
| `MAX_LOCAL_CONCURRENCY` | ✅ | Instance concurrency limit |

---

## Health & Monitoring signals

### `/health/sovereign` (Admin Only)
Endpoint for deep-diagnostic sub-system health.
- **Header**: `X-Admin-Key: <ADMIN_KEY>`
- **Signal**: `llm_engine: Ready`, `memory_matrix: Mounted`.

### Real-Time Intelligence Pulse
```bash
# Monitor live reasoning heartbeats
tail -f logs/orchestrator_pulse.log | grep "metadata"
```

---

## Common Operational Procedures

### Absolute Memory Wipe (Sovereignty)
To fulfill a "Forget Me" request:
```bash
# Atomic wipe of Redis, Firestore, and FAISS
curl -X POST -H "Authorization: Bearer <user_token>" https://levi-monolith/api/privacy/clear-all
```

### Manual Index Maintenance
If retrieval latency drifts > 100ms:
```bash
# Trigger a background maintenance cycle (Internal HMAC required)
curl -X POST -H "X-Internal-Service-Key: <key>" https://levi-monolith/api/admin/memory/gc
```

### Prompt Variant Promotion
To promote a high-performance prompt mutation:
1.  Verify variant score in `prompt_performance` collection.
2.  Set `status: "promoted"` for the target variant.
3.  The system will automatically cache the new baseline.

---

## Troubleshooting

### ❌ `MONOLITH_SATURATED (429)`
- **Cause**: RAM limit or local concurrency gate reached.
- **Fix**: Check Cloud Run scaling limits or increment `MAX_LOCAL_CONCURRENCY` if CPU allows.

### ❌ `SOVEREIGN_ENGINE_OFFLINE (503)`
- **Cause**: Llama-3 weights missing or GGUF load failed.
- **Fix**: Restart service to re-initialize model or verify artifact registry image.

### ❌ `MEMORY_MATRIX_DISCONNECT`
- **Cause**: GCS FUSE mount dropped at `/mnt/vector_db`.
- **Fix**: Verify GCS Bucket permissions and re-deploy instance.

### ❌ `SSE_PULSE_LAG`
- **Cause**: High inference CPU usage blocking the event loop.
- **Fix**: Ensure `4 vCPU` or higher for the monolith service.

---

**LEVI v6.8.5 — Monolith. Secure. Self-Learning.**
*Hardened for Absolute Reasoning Autonomy.*

---

*This runbook is a living document. Update it when adding new services or changing configuration.*
