# LEVI-AI Operations Runbook

> **Version**: v6.8 — Sovereign Hardened Audit  
> **Last Updated**: 2026-04-01  
> **Architecture**: Hybrid Sovereign (FastAPI + Llama-CPP + FAISS + Redis + Firestore)

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Local Development](#local-development)
3. [Sovereign Docker (Production)](#sovereign-docker-production)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Environment Variables Reference](#environment-variables-reference)
6. [Sovereign Health & Monitoring](#sovereign-health--monitoring)
7. [Common Operational Procedures](#common-operational-procedures)
8. [Troubleshooting](#troubleshooting)

---

## System Architecture

```
User Browser
    │
    ▼
[Nginx :80]            ← Static frontend + Reverse Proxy (SSE Buffering OFF)
    │ /api/*
    ▼
[FastAPI Gateway :8000] ← Auth, context-budgeting, Sovereign Routing
    │
    ├── [Llama-CPP]     ← PRIMARY: Local Reasoning (.gguf) 🚀
    ├── [FAISS Index]   ← PRIMARY: Local Vector Memory 🧠
    ├── [Redis :6379]   ← Concurrency Locks, SSE Pub/Sub, Memory Buffer
    ├── [Firestore]     ← SECONDARY: Cold persistence, User Profiles
    └── [Together API]  ← FALLBACK: High-fidelity reasoning
    │
    ▼
[Celery Worker]        ← Async jobs: Pattern distillation, Index maintenance
```

---

## Local Development

### Prerequisites
- Python 3.10+
- Redis 6+
- `.gguf` model weights (e.g., Llama-3-8B)
- Firebase project credentials

### Setup

```bash
# 1. Clone and enter the project
cd LEVI-AI

# 2. Install dependencies (including llama-cpp-python)
pip install -r backend/requirements.txt

# 3. Download weights
mkdir -p backend/models
# Place your llama-3-8b.gguf in backend/models/

# 4. Configure environment
copy .env.example .env
# Set USE_SOVEREIGN_ROUTING=true

# 5. Run the gateway
cd backend
uvicorn gateway:app --reload --port 8000
```

---

## Sovereign Docker (Production)

### Starting all services

```bash
# Build with optimized Llama-CPP wheels
docker compose up --build -d
```

### Services started
| Service | Port | Description |
|---------|------|-------------|
GROQ_API_KEY=your-groq-key
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}  # Raw JSON string
ENVIRONMENT=production
```

### Scaling workers

```bash
# Scale Celery workers to 3 replicas
docker compose up -d --scale worker=3
```

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/`) runs on every push to `main`:

1. **Lint** — `flake8` / `ruff`
2. **Test** — `pytest backend/tests/ -v --tb=short`
3. **Build** — `docker build .`
4. **Deploy** — Push image to registry, rolling restart on Cloud Run / DigitalOcean

### Running Tests Locally

```bash
# Full test suite
python -m pytest backend/tests/ -v --tb=short

# Specific test files
python -m pytest backend/tests/test_memory_buffering.py -v
python -m pytest backend/tests/test_security.py -v
python -m pytest backend/tests/test_reliability.py -v
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key |
| `GROQ_API_KEY` | ✅ | Primary LLM provider |
| `FIREBASE_PROJECT_ID` | ✅ | Firebase project name |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅ | Raw JSON string or file path |
| `REDIS_URL` | ✅ | Redis connection URL |
| `ENVIRONMENT` | ✅ | `production` or `development` — **affects Celery mode** |
| `TOGETHER_API_KEY` | ⚠️ | Required for Pro/Creator Council of Models |
| `SENTRY_DSN` | Recommended | Error tracking |
| `ALERT_WEBHOOK_URL` | Recommended | Discord/Slack circuit-breaker alerts |
| `RAZORPAY_KEY_ID` | For payments | Razorpay API key |
| `ADMIN_KEY` | ✅ | Admin endpoint auth |

---

## Health Checks & Monitoring

### Health Endpoint

```bash
curl http://localhost:8000/health
# Expected:
# {"status": "ok", "database": "ok", "redis": "ok", "auth": "ok", ...}
```

### Redis Metrics (live)

```bash
redis-cli
> GET metrics:total_requests
> LRANGE metrics:latency_ms 0 9
> HGETALL active_instances
```

### Circuit Breaker Status
Circuit breakers automatically send alerts to `ALERT_WEBHOOK_URL` when they open.  
Instances: `ai_service_breaker`, `groq_breaker`, `together_breaker` in `backend/utils/network.py`.

### SSE Activity Stream

```bash
curl -N http://localhost:8000/stream
# Streams live JSON events: chat completions, memory flushes, errors
```

---

## Common Operational Procedures

### Flush Redis Cache

```bash
# Redis CLI — flush all (DANGER: clears everything including sessions)
redis-cli FLUSHDB

# Or targeted: flush only chat caches
redis-cli --scan --pattern "chat_cache:*" | xargs redis-cli DEL
redis-cli --scan --pattern "search:*" | xargs redis-cli DEL
```

### Force-Flush Memory Buffers to Firestore

```bash
# Invoke directly (bypassing Celery Beat)
python -c "
from backend.services.orchestrator.memory_tasks import flush_all_memory_buffers
flush_all_memory_buffers()
"
```

### Trigger Training Data Export

```bash
# Via API (Creator/Admin tier token required)
curl -X POST http://localhost:8000/model/export \
  -H "Authorization: Bearer <your-token>"
```

### View Logs

```bash
# Docker Compose logs
docker compose logs gateway --tail=100 -f
docker compose logs worker --tail=50 -f
docker compose logs beat --tail=20 -f
```

---

## Troubleshooting

### ❌ Celery tasks running synchronously (no queuing)
**Cause**: `ENVIRONMENT` is not set to `production`.  
**Fix**: Set `ENVIRONMENT=production` in your `.env`.

### ❌ Circuit Breaker opens on startup
**Cause**: Groq API key missing or invalid.  
**Fix**: Check `GROQ_API_KEY` is set and valid. The breaker recovers in 30s.

### ❌ `docker compose up --build` fails with "No such file or directory: backend/requirements.prod.txt"
**Cause**: Wrong build context. Must be `.` (root), not `./backend`.  
**Fix**: The updated `docker-compose.yml` now uses `context: .`. Rebuild.

### ❌ Memory facts not being pruned
**Cause**: `created_at` stored as ISO string, compared as ISO string — this is correct and chronologically sortable. If pruning still doesn't work, confirm Beat is running with `ENVIRONMENT=production`.

### ❌ Chat streaming shows full response at once
**Cause**: Frontend is waiting for the full SSE stream before rendering.  
**Fix**: Frontend must process `data:` chunks as they arrive. The backend sends real token chunks via Groq's `stream=True` API for API-routed requests.

### ❌ Redis connection refused at startup
**Cause**: Redis isn't running.  
**Fix in dev**: `redis-server` or `docker run -p 6379:6379 redis:alpine`.  
**Fix in prod**: Ensure the `redis` service is healthy before `gateway` starts (the compose healthcheck handles this).

### ❌ `CORS` errors in browser
**Cause**: Your frontend domain isn't in the allowed origins list.  
**Fix**: Add your domain to `CORS_ORIGINS` env var (comma-separated).

---

*This runbook is a living document. Update it when adding new services or changing configuration.*
