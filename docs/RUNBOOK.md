# 🏃 LEVI-AI Operational Runbook (v14.0.0-Autonomous-SOVEREIGN)

Operations and recovery procedures for the LEVI-AI v14.0.0-Autonomous-SOVEREIGN Absolute Monolith.

---

## 1. Standard Boot Procedure

```powershell
# 1. Launch all infrastructure services
docker-compose up -d

# 2. Verify all containers are healthy
docker-compose ps

# 3. Run 28-point graduation audit
pytest tests/production_readiness_suite.py -v

# 4. Confirm Ollama models are ready
ollama list
# Required: llama3.1:8b, phi3:mini, nomic-embed-text
```

---

## 2. System Health Checks

### Full Connectivity Audit
```powershell
pytest tests/production_readiness_suite.py -v
```
Checks: Redis, Postgres, Neo4j, FAISS, circuit breakers, SSRF, rate limiting.

### Individual Service Pings
```powershell
# Redis
redis-cli ping
# → PONG

# Postgres
psql $DATABASE_URL -c "SELECT version();"

# Neo4j
curl http://localhost:7474/

# Ollama
curl http://localhost:11434/api/tags
```

### Telemetry Health
```powershell
curl http://localhost:8000/health
# Expected: {"status": "online", "version": "v14.0.0-Autonomous-SOVEREIGN"}
```

---

## 3. Emergency Recovery Procedures

### 3.1 Full DR Restore (RTO: < 300s)
```powershell
python -m backend.scripts.restore_drill
```

### 3.2 Mission Blackboard Corruption
```powershell
# Clear transient Redis state
redis-cli --scan --pattern "mission:*" | ForEach-Object { redis-cli del $_ }

# Restart services
docker-compose restart
```

### 3.3 Inference Latency Spikes (> 5s)
```powershell
# Check GPU VRAM pressure
nvidia-smi

# If VRAM > 90%, reduce active semaphore slots in env
# MAX_CONCURRENT=2 (temporary load reduction)

# Do NOT enable CLOUD_FALLBACK unless explicitly required
```

### 3.4 Postgres Failover (PITR)
```powershell
# Restore from WAL archive (5-min granularity)
pg_restore -d levidb ./vault/backups/wal/latest.dump

# Verify data integrity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM missions;"
```

### 3.5 FAISS Index Corruption
```powershell
# Restore from last snapshot
python -m backend.core.snapshot restore --store faiss
```

---

## 4. Scheduled Maintenance

| Task | Frequency | Command |
| :--- | :--- | :--- |
| **Restore Drill** | Weekly | `python -m backend.scripts.restore_drill` |
| **FAISS Reindex** | Monthly | `python -c "from backend.core.vector_store import VectorStore; VectorStore().rebuild_index()"` |
| **FAISS Snapshot** | Every 6h | Automatic via `SnapshotOrchestrator` |
| **Postgres WAL** | Every 5min | Automatic via `postgresql.conf` |
| **Graduation Audit** | On every deploy | `pytest tests/production_readiness_suite.py` |

---

## 5. Performance KPI Thresholds

| Metric | Target | Action if Breached |
| :--- | :--- | :--- |
| **API Latency** | < 500ms | Check Redis circuit breaker, restart Gateway |
| **Vector Recall** | < 100ms | Rebuild FAISS index |
| **Inference (L3.1)** | < 2.5s | Check VRAM pressure, review Semaphore(4) |
| **DB Write** | < 50ms | Check Postgres WAL lag |
| **Fidelity Score (S)** | avg > 0.85 | Review Critic agent configuration |

---

## 6. Logs & Observability

```powershell
# Gateway logs
docker-compose logs -f backend

# Celery worker logs
docker-compose logs -f worker

# SSE Telemetry stream (raw)
curl -N http://localhost:8000/api/v1/telemetry/stream
```

---

© 2026 LEVI-AI SOVEREIGN HUB — Operational Runbook v14.0.0-Autonomous-SOVEREIGN
