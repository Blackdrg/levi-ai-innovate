import os
import subprocess
import datetime
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackupRestore")

BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_postgres():
    """Performs pg_dump for Postgres."""
    logger.info("🐘 [Backup] Starting Postgres dump...")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{BACKUP_DIR}/postgres_backup_{ts}.sql"
    
    # Assuming standard docker-compose service name 'postgres'
    # Environment variables should be used if running inside a container
    try:
        # For this script to work, pg_dump should be available on the host
        # or we execute it via docker exec
        res = subprocess.run([
            "docker", "exec", "levi-ai-postgres-1", 
            "pg_dump", "-U", "levi", "-d", "levi_ai"
        ], capture_output=True, text=True)
        
        if res.returncode == 0:
            with open(filename, "w") as f:
                f.write(res.stdout)
            logger.info(f"✅ [Postgres] Backup saved to {filename}")
        else:
            logger.error(f"❌ [Postgres] Backup failed: {res.stderr}")
    except Exception as e:
        logger.error(f"❌ [Postgres] Backup anomaly: {e}")

def backup_neo4j():
    """Performs neo4j-admin dump."""
    logger.info("🕸️ [Backup] Starting Neo4j dump...")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{BACKUP_DIR}/neo4j_backup_{ts}.dump"
    
    try:
        # Neo4j dump requires the database to be stopped or use 'neo4j-admin database dump'
        res = subprocess.run([
            "docker", "exec", "levi-ai-neo4j-1", 
            "neo4j-admin", "database", "dump", "neo4j", "--to-path=/data/backups"
        ], capture_output=True, text=True)
        
        if res.returncode == 0:
            logger.info(f"✅ [Neo4j] Backup created in /data/backups inside container.")
        else:
            logger.error(f"❌ [Neo4j] Backup failed: {res.stderr}")
    except Exception as e:
        logger.error(f"❌ [Neo4j] Backup anomaly: {e}")

def snapshot_faiss():
    """Snapshots FAISS indices and uploads to (simulated) object storage."""
    logger.info("🧬 [Backup] Starting FAISS index snapshot...")
    source_dir = "backend/data/vector_db"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{BACKUP_DIR}/faiss_snapshot_{ts}"
    
    try:
        if os.path.exists(source_dir):
            shutil.make_archive(archive_name, 'zip', source_dir)
            logger.info(f"✅ [FAISS] Snapshot created: {archive_name}.zip")
            # Simulated upload to S3/GCS
            logger.info("☁️ [FAISS] Uploading to object storage (SIMULATED)...")
        else:
            logger.warning("⚠️ [FAISS] source_dir not found. Skipping.")
    except Exception as e:
        logger.error(f"❌ [FAISS] Snapshot failed: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "backup":
        backup_postgres()
        backup_neo4j()
        snapshot_faiss()
    else:
        logger.info("Usage: python backup_restore.py backup")
