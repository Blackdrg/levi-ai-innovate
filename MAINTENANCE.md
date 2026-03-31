# LEVI-AI: v5.0 Maintenance & Lifecycle Guide 🛠️

This guide outlines the routine operational tasks and lifecycle management for the hardened LEVI-AI platform.

---

## ⚙️ 1. Celery Background Jobs

The backend relies on the `celery` and `celery_beat` services to handle non-blocking workloads.

### Scheduled Tasks (Beat)
| Task | Schedule | Purpose |
|:---|:---|:---|
| `flush_all_memory_buffers` | Every 30s | Flushes Redis memory STM to Firestore MTM. |
| `prune_old_facts` | Daily (00:00) | Removes user facts older than 30 days. |
| `export_training_data` | Weekly (Sun) | Generates JSONL for AI fine-tuning (Creator/Admin). |

### Monitoring Workers
```bash
# Verify worker connectivity and status
celery -A backend.celery_app status

# View live task activity
celery -A backend.celery_app events
```

---

## 💾 2. Database & Data Pruning

LEVI-AI is designed for data privacy. The 30-day pruning policy is the core of "The Soul" memory lifecycle.

### Manual Pruning Query (Firestore)
If automated pruning fails, use the following manual trigger:
```bash
# Manually trigger a pruning cycle for a specific user_id
python -c "from backend.services.orchestrator.memory_utils import prune_old_facts; import asyncio; asyncio.run(prune_old_facts('user_123'))"
```

### Redis Key Management
Flush caches selectively without impacting sessions:
```bash
# Flush only LLM response caches (30-min TTL)
redis-cli --scan --pattern "chat:*" | xargs redis-cli DEL
redis-cli --scan --pattern "search:*" | xargs redis-cli DEL
```

---

## 🛡️ 3. Health & Scaling Operations

### Resource Limits
Default constraints in `docker-compose.yml`:
- **Gateway**: 1.0 CPU, 1GB RAM.
- **Worker**: 1.0 CPU, 1GB RAM (to handle embedding model memory).
- **Beat**: 0.25 CPU, 256MB RAM.

### Scaling UP
Scale your workers horizontally to handle higher message concurrency:
```bash
docker compose up -d --scale worker=3
```

---

## 📝 4. Log Rotation & Archiving

Standard operational logs are stored in the `/logs` directory within the container.
- **Gateway Logs**: `app.log` (Structured JSON).
- **Worker Logs**: `worker.log`.
- **Retention**: Use `logrotate` to keep 30 days of archives.

---

**LEVI — Built for emergence. Maintained for depth.**
