# LEVI-AI: v5.0 Hardened Deployment Checklist ✅

This checklist ensures a successful, zero-downtime deployment for the hardened LEVI-AI v5.0 architecture.

## 🟢 1. Infrastructure Preparation
- [ ] **Network**: Confirm Nginx is configured with `proxy_buffering off;` and proper SSE headers.
- [ ] **Redis Cluster**: Verify session storage and cache connectivity (`redis-cli ping`).
- [ ] **Firestore**: Confirm GCP project ID and service account permissions.
- [ ] **Celery Beat**: Ensure the scheduler is enabled in `docker-compose.yml`.

## 🛡️ 2. Security & Authentication
- [ ] **JTI Check**: Inverted logic bug fix verified in `redis_client.py`?
- [ ] **Secrets Management**: Are `SECRET_KEY` and `ADMIN_KEY` production-strength?
- [ ] **Webhook Alerts**: Is `ALERT_WEBHOOK_URL` set for Discord/Slack circuit breaker notifications?
- [ ] **Environment**: Is `ENVIRONMENT=production` set? (Required for async Celery workers).

## 💾 3. Persistence & Memory
- [ ] **Pruning**: `FACT_EXPIRY_DAYS=30` verified in the daily prune task.
- [ ] **Native Timestamps**: Is `created_at` using native Firestore Timestamps in `memory_utils.py`?
- [ ] **Buffering**: Memory buffering tests (`pytest backend/tests/test_memory_buffering.py`) passed?

## 🚄 4. Performance & LLM
- [ ] **True Streaming**: Token-by-token piping verified on the `/chat` and `/stream` endpoints.
- [ ] **Response Caching**: Verified 30-min Redis cache hit for search/chat agents.
- [ ] **Limits**: Concurrency slots and rate limiting verified via `scripts/load_test.py`.

## 📖 5. Documentation
- [ ] **README.md**: v5.0 branding and pipeline diagram updated.
- [ ] **RUNBOOK.md**: Comprehensive ops & troubleshooting guide verified.
- [ ] **INTEGRATION.md**: Full API reference for chat, stream, and learning endpoints verified.

---

**LEVI — Hardened for production. Built to never fail.**
