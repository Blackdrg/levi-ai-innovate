# 🛠️ LEVI-AI Maintenance Guide (v14.0.0-Autonomous-SOVEREIGN)

Ensuring the stability and performance of the LEVI-AI v14.0.0-Autonomous-SOVEREIGN Distributed Stack requires periodic maintenance across the quad-persistence memory layer and the system optimization pipeline.

---

## 1. System Memory Maintenance

### 1.1 Memory Integration
Verified data from episodic tasks are automatically integrated into long-term knowledge stores.

- **Trigger**: Automatic after every task (if score > 0.85).
- **Manual Force**: `MemoryManager.force_integration(user_id)` via Python REPL.
- **Stores updated**: Neo4j (entity triplets) + HNSW Vault (semantic index).

### 1.2 LearningLoop — Performance Corpus
The `LearningLoop` captures patterns from high-performance tasks (S > 0.85) into the `training_corpus` table.

- **Status**: **[ACTIVE]** — Supports model optimization and performance monitoring.
- **Inspect corpus**: `SELECT COUNT(*) FROM training_corpus;`
- **Data Governance**: Records automatically wiped during user data deletion cycles.

---

## 2. Persistence Layer Maintenance

### 2.1 HNSW Vault Rebuild
Semantic memory retrieval may require optimization after heavy usage. Rebuild the index to maintain search precision.

```python
from backend.core.vector_store import VectorStore
await VectorStore().rebuild_hnsw_index()
```

Recommended frequency: **Monthly** or after 100k+ insertions.

### 2.2 Postgres — WAL & PITR
WAL archiving is automatically enabled at **5-minute intervals** via `postgresql.conf`:

```conf
archive_mode = on
archive_command = 'cp %p /app/vault/backups/wal/%f'
archive_timeout = 300
```

To restore to a specific point in time:
```bash
pg_restore -d levidb ./vault/backups/wal/<snapshot>.dump
```

### 2.3 Redis — AOF Health Check
`appendfsync everysec` is confirmed active. Verify with:
```bash
redis-cli CONFIG GET appendfsync
# Expected: ["appendfsync", "everysec"]
```

### 2.4 Neo4j — Graph Backup
Automated 12-hour backup via `neo4j-admin`:
```bash
neo4j-admin database backup neo4j --to-path=/backups/neo4j
```

### 2.5 HNSW Vault — Snapshot Schedule
Automated every 6 hours via `SnapshotOrchestrator`. Manual trigger:
```python
from backend.core.snapshot import SnapshotOrchestrator
await SnapshotOrchestrator().backup_hnsw()
```

---

## 3. Resource Hygiene

### 3.1 Memory Pruning (Automatic)
The `MemoryPruner` background task runs weekly, removing low-scoring records (score < 0.5) from HNSW Vault to maintain index quality.

Audit via worker logs:
```bash
docker-compose logs worker | grep "pruning_cycle"
```

### 3.2 Redis Orphan Key Cleanup
Task state keys expire automatically (TTL: 3600s). For manual cleanup:
```bash
redis-cli --scan --pattern "task:*" | ForEach-Object { redis-cli del $_ }
```

Event stream inspection:
```bash
redis-cli LLEN dcn:task_queue
redis-cli XINFO STREAM dcn:gossip
```

### 3.3 Security Key Rotation
Rotate system secrets periodically for enhanced security:
1. Generate new 64-char hex key: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Update `.env` and `docker-compose.yml`.
3. Restart services: `docker-compose restart`.

---

## 4. Performance Diagnostics

### 4.1 Production Audit Suite
```bash
pytest tests/production_readiness_suite.py -v
```

### 4.2 KPI Thresholds
| Metric | Target | Alarm Threshold |
| :--- | :--- | :--- |
| **API Latency** | < 500ms | > 1000ms |
| **Vector Recall** | < 100ms | > 250ms |
| **Inference (L3.3)** | < 1.0s | > 2.0s |
| **Evaluation Score (S)** | avg > 0.85 | avg < 0.70 |
| **Resource Units** | < 50 RU | > 100 RU |

### 4.3 Disaster Recovery Drill
Run weekly to verify RTO compliance:
```bash
python -m backend.scripts.restore_drill
# Target: All components restored in < 300 seconds
```

---

© 2026 LEVI-AI Sovereign OS — Maintenance Specification v14.0.0 Production Stable
