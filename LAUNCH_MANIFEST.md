# LEVI-AI: v5.0 Launch Manifest (Pre-Flight) 🚀

This document lists the mandatory pre-flight checks for the hardened LEVI-AI platform.

---

## 🛠️ 1. Infrastructure Checks

- [ ] **Redis**: Reachable? `redis-cli ping`
- [ ] **Firestore**: Connectivity verified? Check `/health`
- [ ] **Nginx**: `proxy_buffering off;` set? (Required for SSE)
- [ ] **Celery**: `beat` scheduler is running? `docker compose logs beat`

---

## 🛡️ 2. Security & Auth

- [ ] **JTI Logic**: Verified in `redis_client.py`?
- [ ] **Environment**: `ENVIRONMENT=production` set in `.env`?
- [ ] **Webhook**: `ALERT_WEBHOOK_URL` configured for circuit breaker alerts?
- [ ] **Secrets**: `SECRET_KEY` and `ADMIN_KEY` are long, random strings?

---

## 💾 3. Memory & Data Lifecycle

- [ ] **Pruning**: `FACT_EXPIRY_DAYS=30` configured correctly?
- [ ] **Timestamps**: Native Firestore Timestamps used for `created_at`?
- [ ] **Buffers**: Memory buffering tests passed? `pytest backend/tests/test_memory_buffering.py`

---

## 🚄 4. Performance & LLM

- [ ] **Streaming**: True token-by-token streaming verified? Check `/chat` endpoint.
- [ ] **Caching**: Response caching active? Identical queries should reach `cached: true`.
- [ ] **Limits**: Concurrency slots and rate limiting verified via `scripts/load_test.py`?

---

## 📖 5. Documentation Review

- [ ] **README**: Updated to v5.0 branding?
- [ ] **RUNBOOK**: Operations and troubleshooting guide verified?
- [ ] **DIAGNOSTICS**: Health signals and log patterns documented?

---

**LEVI — Built for emergence. Launched for depth.**
