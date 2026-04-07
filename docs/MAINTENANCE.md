# 🛠️ LEVI-AI Maintenance Guide (v1.0.0-RC1)

Ensuring the stability and fidelity of the LEVI-AI v1.0.0-RC1 Distributed Stack requires periodic maintenance across the quad-persistence memory fabric and the cognitive evolution pipeline.

---

## 1. Cognitive Memory Maintenance

### 1.1 Memory Crystallization
High-fidelity facts from episodic missions are automatically distilled into long-term knowledge.

- **Trigger**: Automatic after every mission (if score > 0.85).
- **Manual Force**: `MemoryManager.force_crystallization(user_id)` via Python REPL.
- **Stores updated**: Neo4j (entity triplets) + FAISS (semantic index).

### 1.2 LearningLoop — Pattern Corpus [UPDATED]
The `LearningLoop` captures patterns from high-fidelity missions (S > 0.85) into the `training_corpus` table.

- **Status**: **[STUB]** — Data is captured only. Model weights are NOT modified in v1.0.0.
- **Inspect corpus**: `SELECT COUNT(*) FROM training_corpus;`
- **GDPR**: Records automatically wiped with 5-tier user deletion.

---

## 2. Persistence Layer Maintenance

### 2.1 FAISS Index Rebuild
Semantic memory may drift in accuracy for heavy-usage tenants. Rebuild to optimize retrieval.

```python
from backend.core.vector_store import VectorStore
await VectorStore().rebuild_index()
```

Recommended frequency: **Monthly** or after 100k+ insertions.

### 2.2 Postgres — WAL & PITR [UPDATED]
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

### 2.3 Redis — AOF Health Check [UPDATED]
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

### 2.5 FAISS — Snapshot Schedule
Automated every 6 hours via `SnapshotOrchestrator`. Manual trigger:
```python
from backend.core.snapshot import SnapshotOrchestrator
await SnapshotOrchestrator().backup_faiss()
```

---

## 3. Resource Hygiene

### 3.1 Memory Pruning (Automatic)
The `MemoryPruner` Celery task runs weekly, removing low-importance memories (score < 0.5) from FAISS.

Audit via Celery worker logs:
```bash
docker-compose logs worker | grep "pruning_cycle"
```

### 3.2 Redis Orphan Key Cleanup [UPDATED]
Mission state keys expire automatically (TTL: 3600s). For manual orphan cleanup:
```bash
redis-cli --scan --pattern "mission:*" | ForEach-Object { redis-cli del $_ }
```

DCN task queue inspection:
```bash
redis-cli LLEN dcn:task_queue
redis-cli XINFO STREAM dcn:gossip
```

### 3.3 Vault Key Rotation
Rotate `AUDIT_CHAIN_SECRET` and `DCN_SECRET` periodically:
1. Generate new 64-char hex key: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Update `.env` and `docker-compose.yml`.
3. Restart services: `docker-compose restart`.

---

## 4. Performance Diagnostics

### 4.1 Full Audit Suite
```bash
pytest tests/production_readiness_suite.py -v
```

### 4.2 KPI Thresholds
| Metric | Target | Alarm Threshold |
| :--- | :--- | :--- |
| **API Latency** | < 500ms | > 1000ms |
| **Vector Recall** | < 100ms | > 250ms |
| **Inference (L3.1)** | < 2.0s | > 4.0s |
| **Fidelity Score (S)** | avg > 0.85 | avg < 0.70 |
| **CU per Mission** | < 50 CU | > 100 CU |

### 4.3 DR Restore Drill [NEW]
Run weekly to verify RTO compliance:
```bash
python -m backend.scripts.restore_drill
# Target: All 4 stores restored in < 300 seconds
```

---

© 2026 LEVI-AI SOVEREIGN HUB — Maintenance Specification v1.0.0-RC1
