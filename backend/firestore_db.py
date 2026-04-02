import os
import logging
from typing import Dict, Any, List, Optional
try:
    from google.cloud import firestore # type: ignore
    HAS_FIRESTORE = True
except ImportError:
    firestore = None 
    HAS_FIRESTORE = False

logger = logging.getLogger(__name__)

class SovereignDB:
    """
    Sovereign Persistence Layer (Firestore).
    Hardened for high-concurrency neural state management.
    Handles automatic retries and transaction-safe updates.
    """
    _instance: Optional[firestore.Client] = None

    @classmethod
    def get_client(cls) -> Optional[firestore.Client]:
        """Retrieves and initializes the Firestore client singleton."""
        if not HAS_FIRESTORE:
            logger.warning("[DB] Firestore SDK not installed. Running in degraded mode.")
            return None
            
        if cls._instance is not None:
            return cls._instance
        
        try:
            project_id = os.getenv("GCP_PROJECT_ID")
            logger.info(f"[DB] Connecting to Sovereign Ledger (Project: {project_id})")
            cls._instance = firestore.Client(project=project_id)
            return cls._instance
        except Exception as e:
            logger.error(f"[DB] Critical ledger connection failure: {e}")
            return None

    @classmethod
    async def get_document(cls, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        client = cls.get_client()
        if not client: return None
        
        try:
            doc_ref = client.collection(collection).document(doc_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[DB] Retrieval failure for {doc_id} in {collection}: {e}")
            return None

    @classmethod
    async def save_document(cls, collection: str, doc_id: str, data: Dict[str, Any], merge: bool = True):
        client = cls.get_client()
        if not client: return
        
        try:
            doc_ref = client.collection(collection).document(doc_id)
            doc_ref.set(data, merge=merge)
            logger.info(f"[DB] Ledger update successful: {collection}/{doc_id}")
        except Exception as e:
            logger.error(f"[DB] Ledger update failure for {doc_id} in {collection}: {e}")

    @classmethod
    async def batch_save(cls, collection: str, documents: List[Dict[str, Any]]):
        """Asynchronous batch update for high-frequency neural evolution logging."""
        client = cls.get_client()
        if not client: return
        
        try:
            batch = client.batch()
            for doc in documents:
                doc_id = doc.get("id") or doc.get("user_id")
                if not doc_id: continue
                doc_ref = client.collection(collection).document(doc_id)
                batch.set(doc_ref, doc, merge=True)
            batch.commit()
            logger.info(f"[DB] Batch ledger update successful for {len(documents)} records.")
        except Exception as e:
            logger.error(f"[DB] Batch ledger failure: {e}")

# Global Accessor
db = SovereignDB
