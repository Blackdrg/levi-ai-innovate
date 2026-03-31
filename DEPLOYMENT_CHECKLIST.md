# LEVI-AI: v5.0 Hardened Deployment Checklist ✅

This checklist ensures a successful, zero-downtime deployment for the hardened LEVI-AI v5.0 architecture.

## 🟢 1. Infrastructure Preparation
- [x] **Network**: Confirm Nginx is configured with `proxy_buffering off;` and proper SSE headers. (Verified in `nginx.conf`)
- [ ] **Redis Cluster**: Verify session storage and cache connectivity (`redis-cli ping`). (**Runtime Check Required**)
- [ ] **Firestore**: Confirm GCP project ID and service account permissions. (**Runtime Check Required**)
- [x] **Celery Beat**: Ensure the scheduler is enabled in `docker-compose.yml`. (Verified in codebase)

## 🛡️ 2. Security & Authentication
- [x] **JTI Check**: Inverted logic bug fix verified in `redis_client.py`? (Verified & Fixed)
- [ ] **Secrets Management**: Are `SECRET_KEY` and `ADMIN_KEY` production-strength? (**User Check Required**)
- [ ] **Webhook Alerts**: Is `ALERT_WEBHOOK_URL` set for Discord/Slack circuit breaker notifications? (**User Check Required**)
- [x] **Environment**: Is `ENVIRONMENT=production` set? (Verified in `.env.example`/code defaults).

## 💾 3. Persistence & Memory
- [x] **Pruning**: `FACT_EXPIRY_DAYS=30` verified in the daily prune task. (Verified in `memory_utils.py`)
- [x] **Native Timestamps**: Is `created_at` using native Firestore Timestamps in `memory_utils.py`? (Verified & Fixed)
- [ ] **Buffering**: Memory buffering tests (`pytest backend/tests/test_memory_buffering.py`) passed? (**Runtime Test Required**)

## 🚄 4. Performance & LLM
- [x] **True Streaming**: Token-by-token piping verified on the `/chat` and `/stream` endpoints. (Verified in `router.py`)
- [x] **Response Caching**: Verified 30-min Redis cache hit for search/chat agents. (Verified in `agent_registry.py`)
- [ ] **Limits**: Concurrency slots and rate limiting verified via `scripts/load_test.py`? (**Runtime Test Required**)

## 📖 5. Documentation
- [x] **README.md**: v5.0 branding and pipeline diagram updated. (Verified)
- [x] **RUNBOOK.md**: Comprehensive ops & troubleshooting guide verified. (Verified)
- [x] **INTEGRATION.md**: Full API reference for chat, stream, and learning endpoints verified. (Verified)

---

**LEVI — Hardened for production. Built to never fail.**
