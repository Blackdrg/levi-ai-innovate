# LEVI-AI: Hardened Diagnostics & Health Master (v6.8) 🔍

This guide provides technical signals, log analysis patterns, and troubleshooting steps for the hardened LEVI-AI v6.8 Sovereign platform.

---

## 📈 1. Primary Health Signals

### `/health/sovereign` Endpoint
Expects: `HTTP 200` with JSON body:
- `status`: `ok` (Global)
- `local_engine`: `ready` (Llama-CPP)
- `memory`: `synced` (FAISS Indices)
- `redis`: `reachable` (Session/Cache)
- `version`: `6.8.4`

### Metric: `metrics:sovereign_routing_ratio`
Tracks the percentage of requests handled by the local engine vs. cloud fallbacks. Target: >80%.

---

## 📝 2. Structured Log Analysis

All logs follow a JSON format for integration with Cloud Logging / Sentry.

### Example: Sovereign Decision Log
```json
{
    "timestamp": "2026-04-01T12:00:00Z",
    "level": "INFO",
    "request_id": "orch_abc123",
    "intent": "complex_query",
    "engine_route": "sovereign",
    "model": "llama-3-8b.gguf",
    "memory_hits": 4,
    "latency_ms": 450,
    "circuit_breaker": "CLOSED"
}
```

### Log Queries
- **Find all local-routed requests**: `jsonPayload.engine_route="sovereign"`
- **Monitor FAISS hit rate**: `jsonPayload.memory_hits > 0`
- **Track Local Engine failures**: `jsonPayload.level="ERROR" AND jsonPayload.engine_route="sovereign"`

---

## 🛡️ 3. Circuit Breaker Diagnostics

The circuit breaker (`network.py`) prevents cascading failures when the Local Engine or Cloud providers (Together) are unstable.

| State | Indication | Action |
|:---|:---|:---|
| **CLOSED** | Healthy | Normal operation. |
| **OPEN** | ENGINE DOWN | Automated fallback to Cloud (Together) active; Webhook alert sent. |
| **HALF_OPEN** | HEALING | Testing engine with single-request probe. |

---

## ❌ 4. Common Sovereign Errors

### `LEVI_SOVEREIGN_01 — Model Not Found`
- **Cause**: `.gguf` weight file missing from `backend/models/`.
- **Diagnostics**: Check `LOCAL_MODEL_PATH` in `.env`.

### `LEVI_MEMORY_88 — FAISS Corruption`
- **Cause**: Index file corrupted on disk or memory mismatch.
- **Diagnostics**: Run `python scripts/verify_indices.py`.

### `LEVI_SSE_20 — Pulse Drop`
- **Cause**: Nginx buffer timeout or high CPU usage on local inference.
- **Diagnostics**: Check `top` for `levi-api` CPU spikes.

---

## 🛠️ 5. Instant Diagnostic Tools

```bash
# Verify local model loading
python -c "from backend.sd_engine import LocalEngine; print(LocalEngine().status())"

# View the last 100 intelligence pulses
tail -n 100 /var/log/levi/orchestrator.log | grep "type: activity"

# Manually trigger a FAISS index consolidation
celery -A backend.celery_app call backend.services.orchestrator.memory_tasks.run_global_maintenance
```

---

**LEVI v6.8 — Architected for depth. Documented for clarity. Sovereign by design.**
