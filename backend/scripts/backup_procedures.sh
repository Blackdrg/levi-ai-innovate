#!/bin/bash
# Sovereign OS Backup Procedures v22.1

# 1. Postgres Database Dump
echo "🐘 Archiving SQL Fabric (Postgres)..."
docker exec postgres pg_dump -U levi -d levi_ai > ./backups/postgres_$(date +%Y%m%d_%H%M%S).sql

# 2. Neo4j Graph Dump
echo "🕸️  Snapshotting Knowledge Graph (Neo4j)..."
docker exec neo4j bin/neo4j-admin database dump neo4j --to-path=/backups/neo4j_$(date +%Y%m%d_%H%M%S).dump

# 3. FAISS Vector Snapshots
echo "🧬 Pulsing Vector Store Snapshots (FAISS)..."
# Zip the indexes directory which contains .index and .wal files
zip -r ./backups/faiss_$(date +%Y%m%d_%H%M%S).zip ./backend/data/indexes/

# 4. Storage Upload (Simulated S3/GCS)
echo "☁️  Syncing to Sovereign Vault (Cold Storage)..."
# gsutil cp ./backups/* gs://levi-sovereign-vault/
