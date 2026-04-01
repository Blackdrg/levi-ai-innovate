# LEVI-AI: Hardened Diagnostics & Health Master (v6.8.5) 🔍

This guide provides technical signals, log analysis patterns, and troubleshooting steps for the hardened LEVI-AI v6.8.5 Sovereign Monolith.

---

## 📈 1. Primary Health Signals

### `/health/sovereign` Endpoint (Admin Only)
Expects: `HTTP 200` with `X-Admin-Key` header. JSON body:
- `status`: `Green` (Global)
- `llm_engine`: `Ready` (Llama-3-8B GGUF)
- `memory_matrix`: `Mounted` (GCS FUSE at /mnt/vector_db)
- `faiss_hits`: `Synced` (Active binary indices)
- `concurrency`: `Active` (Gate: MAX_LOCAL_CONCURRENCY=2)
- `version`: `6.8.5`

### Metric: `metrics:sovereign_ratio`
Tracks the percentage of requests handled by the local engine (Monolith) vs. API fallbacks. Target: >90% for absolute sovereignty.

---

## 📝 2. Structured Log Analysis (JSON)

All logs follow a production-grade JSON format for Cloud Logging / Sentry integration.

### Example: Monolith Routing Decision
```json
{
    "timestamp": "2026-04-01T22:45:00Z",
    "level": "INFO",
    "request_id": "req_monolith_f01",
    "intent": "chat",
    "route": "LOCAL",
    "model": "Llama-3-8B.gguf",
    "latency_ms": 42,
    "concurrency_load": 1,
    "circuit": "CLOSED"
}
```

### Log Queries
- **Monitor Concurrency Gate**: `jsonPayload.concurrency_load >= 2`
- **Track Sovereignty Failovers**: `jsonPayload.route != "LOCAL"`
- **Trace Full Memory Pulls**: `jsonPayload.memory_hits > 10`

---

## 🛡️ 3. Resilience & Circuit Breakers

The `Standardizer` and `LocalEngine` breakers prevent cascading failures during RAM saturation.

| State | Indication | Action |
|:---|:---|:---|
| **CLOSED** | Healthy | Normal monolithic operation. |
| **OPEN** | SATURATED | RAM/CPU limit reached; system triggers API fallback for high-complexity tasks. |
| **HALF_OPEN** | HEALING | Testing local GGUF engine with single-token probe. |

---

## ❌ 4. Common Monolith Deviations

### `SOVEREIGN_ENGINE_OFFLINE (503)`
- **Cause**: GGUF weights missing or Llama-CPP failed to initialize.
- **Diagnostics**: `scripts/verify_production.py --prod` check `Local_GGUF` circuit.

### `MONOLITH_SATURATED (429)`
- **Cause**: 8Gi RAM limit reached or `MAX_LOCAL_CONCURRENCY` exceeded.
- **Diagnostics**: Monitor Cloud Run 'Memory Utilization' spikes.

### `MEMORY_MATRIX_DISCONNECT`
- **Cause**: GCS FUSE mount dropped at `/mnt/vector_db`.
- **Diagnostics**: `ls /mnt/vector_db` check for user indices.

---

## 🛠️ 5. Instant Diagnostic Tools (Production)

```bash
# Verify v6.8.5 absolute sovereignty health
python scripts/verify_production.py --prod

# Check real-time intelligence pulses
curl -N -H "X-Admin-Key: <key>" https://levi-monolith-url/api/status/pulse

# Trigger manual FAISS distillation
celery -A backend.celery_app call backend.services.orchestrator.memory_manager.distill_core_memory
```

---

**LEVI v6.8.5 — Architected for depth. Documented for clarity. Sovereign by design.**
