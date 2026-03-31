# LEVI-AI: Hardened Diagnostics & Health Master (v5.0) 🔍

This guide provides technical signals, log analysis patterns, and troubleshooting steps for the hardened LEVI-AI platform.

---

## 📈 1. Primary Health Signals

### `/health` Endpoint
Expects: `HTTP 200` with JSON body:
- `status`: `ok` (Global)
- `database`: `connected` (Firestore)
- `redis`: `reachable` (Session/Cache)
- `auth`: `verified` (Firebase)
- `version`: `5.0`

### Metric: `metrics:total_requests` (Redis-backed)
Tracks real-time system throughput. Monitor for sudden drops which could indicate an Nginx ingress failure.

---

## 📝 2. Structured Log Analysis

All logs follow a JSON format for integration with Cloud Logging / Sentry.

### Example: Decision Log
```json
{
    "timestamp": "2026-03-31T12:00:00Z",
    "level": "INFO",
    "request_id": "req-abc123",
    "trace_id": "tr-xyz789",
    "intent": "complex_query",
    "engine_route": "api",
    "latency_ms": 1245,
    "cached": false,
    "circuit_breaker": "CLOSED"
}
```

### Log Queries
- **Find all API-routed requests**: `jsonPayload.engine_route="api"`
- **Monitor cache hit rate**: `jsonPayload.cached=true`
- **Track Circuit Breaker trips**: `jsonPayload.circuit_breaker="OPEN"`

---

## 🛡️ 3. Circuit Breaker Diagnostics

The circuit breaker (`network.py`) prevents cascading failures when external LLM providers (Groq, Together) are unreachable.

| State | Indication | Action |
|:---|:---|:---|
| **CLOSED** | Healthy | Normal operation. |
| **OPEN** | SERVICE DOWN | Automated fallback to `local_engine` active; Webhook alert sent. |
| **HALF_OPEN** | HEALING | Testing connection with single-request probe. |

---

## ❌ 4. Common Hardened Errors

### `LEVI_AUTH_99 — JTI Blacklisted`
- **Cause**: User token has been revoked or session invalidated.
- **Diagnostics**: Check `redis_client.py` logs for specific JTI match.

### `LEVI_MEMORY_50 — Pruning Stalled`
- **Cause**: Background Celery job failed or `ENVIRONMENT` not set to `production`.
- **Diagnostics**: Check `celery worker` logs for `prune_old_facts` task.

### `LEVI_SSE_10 — Buffer Timeout`
- **Cause**: Nginx is buffering responses, blocking tokens until the stream ends.
- **Diagnostics**: Verify `proxy_buffering off;` in `nginx.conf`.

---

## 🛠️ 5. Instant Diagnostic Tools

```bash
# Verify redis connectivity from within the gateway container
redis-cli ping

# View the last 100 decision logs
tail -n 100 /var/log/levi/orchestrator.log | grep "engine_route"

# Manually trigger a memory buffer flush
python -c "from backend.services.orchestrator.memory_tasks import flush_all_memory_buffers; flush_all_memory_buffers()"
```

---

**LEVI — Architected for depth. Documented for clarity.**
