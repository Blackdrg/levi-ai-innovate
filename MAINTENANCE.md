# LEVI v2.0 — MAINTENANCE.md

Operational runbook for keeping LEVI healthy in production.

---

## 🩺 Daily Health Checks

```bash
BASE=https://levi-api.a.run.app

# 1. Full health check
curl $BASE/health
# → {"status":"ok","database":"ok","redis":"ok"}

# 2. Celery worker status
celery -A backend.celery_app status

# 3. Redis memory usage (Upstash console or CLI)
redis-cli -u $REDIS_URL info memory | grep used_memory_human

# 4. Check memory debounce queue depth
redis-cli -u $REDIS_URL llen memory:pending_flush
# Should be < 200 entries between flushes
```

---

## 🔧 Orchestrator Monitoring

### Decision Log Pattern
Every routed request emits a structured log. Filter for routing anomalies:
```
# Cloud Logging query
resource.type="cloud_run_revision"
jsonPayload.message=~"Decision:"
```

### Cost Alerts
Watch for unexpected API route spikes:
```
# Alert if LOCAL route % drops below 40% (suggests intent detection drift)
jsonPayload.route="api" AND timestamp > "now-1h"
```

### Key Metrics to Watch
| Metric | Healthy | Warning |
|--------|---------|---------|
| `route=local` % | ≥ 50% | < 30% |
| p95 latency | < 2,000ms | > 3,000ms |
| `validate_response` fallback rate | < 1% | > 5% |
| Memory store background failures | 0 | > 0 |

---

## 🔄 Celery Beat Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `flush_memory_buffer` | Every 5 min | Flush Redis → Firestore debounce buffer |
| `prune_old_facts` | Nightly | Remove 30-day-old semantic facts |
| `cleanup_zombie_jobs` | Every 15 min | Fail stuck processing jobs |

Check beat schedule is running:
```bash
# Should see heartbeat logs every 5 min
celery -A backend.celery_app inspect scheduled
```

---

## 🚨 Incident Response

### Orchestrator Returns Empty Response
**Should not happen** — the 3-tier fallback guarantees a response. If it does:
1. Check `validate_response` logs for all 3 fallback stages failing
2. Verify `local_engine.py` `FALLBACK_RESPONSE` is not empty
3. Check if `_LEVI_BACKGROUND_TASKS` set is leaking (memory GC issue)

### LLM Latency Spike (p95 > 5s)
1. Check Groq status page: [status.groq.com](https://status.groq.com)
2. Temporary mitigation: bump `complexity` threshold in `route_request()` to route more traffic LOCAL
3. Enable local-only mode: set env `FORCE_LOCAL_ROUTING=true` (if implemented)

### Redis Down
- Rate limiting disabled (falls back to memory)
- Session STM unavailable (context window lost)
- Memory debounce buffer lost (unflushed writes)
- Celery broker down → queue all tasks

→ Restart Upstash instance. Workers will reconnect automatically.

### Firestore Quota Exceeded
- Mid-term memory writes fail (buffered in Redis)
- Long-term fact extraction queued in Celery
- Health endpoint returns `"database":"error"` but service stays UP

→ Check Firestore quotas in GCP console. Increase if needed.

---

## 🔐 Key Rotation

### Rotating GROQ_API_KEY
1. Generate new key at console.groq.com
2. Update GitHub secret `GROQ_API_KEY`
3. Redeploy Cloud Run: `gcloud run deploy levi-backend --region us-central1`
4. Verify: `curl $BASE/health`

### Rotating SECRET_KEY (JWT)
> [!CAUTION]
> Rotating `SECRET_KEY` invalidates ALL active user sessions immediately.
1. Generate: `python -c "import secrets; print(secrets.token_hex(64))"`
2. Update GitHub secret
3. Redeploy
4. All users will be signed out and need to re-authenticate

---

## 📈 Scaling

### Horizontal Scale (Cloud Run)
```bash
gcloud run services update levi-backend \
  --max-instances 20 \
  --concurrency 100 \
  --region us-central1
```

### Vertical Scale (Memory)
```bash
gcloud run services update levi-backend \
  --memory 8Gi \
  --region us-central1
```

### Load Test Before Scaling
```bash
python scripts/load_test.py --users 500 --target https://levi-api.a.run.app
# Target: success_rate >= 95%, p95 < 2,000ms
```

---

## 🗂️ Log Queries (Cloud Logging)

```bash
# All orchestrator decisions in last hour
resource.type="cloud_run_revision"
jsonPayload.message=~"Decision:"
timestamp >= "2026-01-01T00:00:00Z"

# Validation fallbacks (should be near zero)
jsonPayload.message=~"Response validation failed"

# Memory store failures
severity=ERROR jsonPayload.message=~"store_memory"

# Rate limit hits
jsonPayload.message=~"RATE_LIMIT_EXCEEDED"
```

---

## 🔁 Testing in Production

```bash
# Smoke test all engine routes
python scripts/load_test.py --users 10 --target https://levi-api.a.run.app

# Unit tests (should always run clean)
pytest tests/test_orchestrator.py -v --tb=short
# Expected: 42 passed, 0 failed
```
