import os
import logging
import subprocess
import datetime

logger = logging.getLogger(__name__)

class SovereignBackup:
    """
    Sovereign Backup & Disaster Recovery v13.0.0.
    Orchestrates high-fidelity snapshots of the persistent memory stores.
    """
    
    BACKUP_ROOT = os.getenv("BACKUP_PATH", "backend/data/backups")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "levi_db")
    NEO4J_DB = "neo4j"
    HNSW_PATH = "backend/data/vector_db"

    @classmethod
    def run_full_backup(cls):
        """Standard v13 Full Recovery Cycle."""
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"[Backup] Starting Absolute Monolith Snapshot: {now}")
        
        results = [
            cls.backup_postgres(now),
            cls.backup_neo4j(now),
            cls.backup_vector_store(now)
        ]
        
        if all(results):
            logger.info("[Backup] Full graduation snapshot complete.")
        else:
            logger.error("[Backup] Snapshot anomalies detected.")

    @classmethod
    def backup_postgres(cls, timestamp: str) -> bool:
        """Postgres pg_dump snapshot."""
        path = os.path.join(cls.BACKUP_ROOT, f"postgres_{timestamp}.sql")
        os.makedirs(cls.BACKUP_ROOT, exist_ok=True)
        try:
            logger.info(f"[Backup] Dumping Postgres to {path}...")
            # Note: Expects local pg_dump and password in PGPASSWORD or .pgpass
            subprocess.run(["pg_dump", "-U", "levi_user", "-d", cls.POSTGRES_DB, "-f", path], check=True)
            return True
        except Exception as e:
            logger.error(f"[Backup] Postgres dump failed: {e}")
            return False

    @classmethod
    def backup_neo4j(cls, timestamp: str) -> bool:
        """Neo4j dump snapshot."""
        path = os.path.join(cls.BACKUP_ROOT, f"neo4j_{timestamp}.dump")
        try:
            logger.info(f"[Backup] Dumping Neo4j to {path}...")
            # Note: Requires neo4j-admin to be in path
            subprocess.run(["neo4j-admin", "database", "dump", cls.NEO4J_DB, f"--to-path={path}"], check=True)
            return True
        except Exception as e:
            logger.error(f"[Backup] Neo4j dump failed: {e}")
            return False

    @classmethod
    def backup_vector_store(cls, timestamp: str) -> bool:
        """HNSW index file archive."""
        import tarfile
        path = os.path.join(cls.BACKUP_ROOT, f"vector_db_{timestamp}.tar.gz")
        try:
            logger.info(f"[Backup] Archiving Vector DB to {path}...")
            with tarfile.open(path, "w:gz") as tar:
                tar.add(cls.HNSW_PATH, arcname=os.path.basename(cls.HNSW_PATH))
            return True
        except Exception as e:
            logger.error(f"[Backup] Vector DB archive failed: {e}")
            return False

if __name__ == "__main__":
    SovereignBackup.run_full_backup()
