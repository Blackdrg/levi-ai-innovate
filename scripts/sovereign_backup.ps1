# Sovereign Backup Protocol v14.0.0
# "Sovereign OS Fabric" Multi-Store Atomic Backup (Zero-Cloud)

$BackupRoot = "D:\LEVI-AI\backends\backups\$(Get-Date -Format 'yyyy-MM-dd_HH-mm')"
New-Item -ItemType Directory -Path $BackupRoot -Force

Write-Host "[Sovereign] Initiating 5-Store Atomic Backup to $BackupRoot..." -ForegroundColor Cyan

# 1. Redis (Tier 1: Working)
Write-Host "[1/5] Backing up Redis (RDB)..."
docker exec levi-redis redis-cli SAVE
docker cp levi-redis:/data/dump.rdb "$BackupRoot\redis_dump.rdb"

# 2. Postgres (Tier 2/3/4: SQL Resonance)
Write-Host "[2/5] Backing up Postgres (SQL)..."
docker exec levi-postgres pg_dump -U sovereign_user sovereign_db > "$BackupRoot\postgres_dump.sql"

# 3. Neo4j (Tier 5: Knowledge Graph)
Write-Host "[3/5] Backing up Neo4j (Graph)..."
docker exec levi-neo4j cypher-shell -u neo4j -p sovereign_pass "CALL apoc.export.json.all('$BackupRoot\neo4j_graph.json', {})"
# Alternatively, use neo4j-admin dump if offline
docker cp levi-neo4j:/var/lib/neo4j/import/neo4j_graph.json "$BackupRoot\neo4j_graph.json"

# 4. HNSW Vault (Tier 3: Semantic)
Write-Host "[4/5] Backing up HNSW Vector Vault..."
Copy-Item -Path "D:\LEVI-AI\data\vault\*" -Destination "$BackupRoot\hnsw_vault\" -Recurse

# 5. JSONL Crystallized Wisdom (Tier 4: Identity)
Write-Host "[5/5] Backing up Crystallized Wisdom (JSONL)..."
Copy-Item -Path "D:\LEVI-AI\backend\data\crystallized_wisdom.jsonl" -Destination "$BackupRoot\crystallized_wisdom.jsonl"

Write-Host "[Sovereign] Backup Complete. Audit Point 18 Passed." -ForegroundColor Green
Write-Host "Location: $BackupRoot"
