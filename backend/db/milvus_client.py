import os
import logging
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, utility, CollectionSchema, FieldSchema, DataType

logger = logging.getLogger(__name__)

class MilvusClient:
    """
    Sovereign v14.2: Milvus Global Memory Tier.
    Provides a distributed vector database for cross-region cognitive consistency.
    """
    _connected = False

    @classmethod
    def connect(cls):
        if cls._connected:
            return True
        
        # Priority: MILVUS_HOST (for K8s internal) -> MILVUS_URI (for remote/cloud)
        host = os.getenv("MILVUS_HOST", "localhost")
        port = os.getenv("MILVUS_PORT", "19530")
        uri = os.getenv("MILVUS_URI", f"http://{host}:{port}")
        token = os.getenv("MILVUS_TOKEN", "")
        
        try:
            connections.connect(
                alias="default", 
                uri=uri, 
                token=token,
                timeout=10
            )
            cls._connected = True
            logger.info(f"[Milvus] Connected to Global Memory Tier: {uri}")
            return True
        except Exception as e:
            logger.error(f"[Milvus] Connection failed: {e}")
            return False

    @classmethod
    async def ensure_collection(cls, collection_name: str, dimension: int = 1536):
        """Ensures the secondary global collection exists with the correct schema."""
        if not cls.connect(): return None
        
        if utility.has_collection(collection_name):
            return Collection(collection_name)
        
        # Schema for Sovereign Memory (Tier 5)
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name="timestamp", dtype=DataType.INT64)
        ]
        schema = CollectionSchema(fields, "LEVI-AI Global Sovereign Memory")
        collection = Collection(collection_name, schema)
        
        # Create Index (HNSW for high-fidelity retrieval)
        index_params = {
            "metric_type": "L2",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
        collection.create_index(field_name="vector", index_params=index_params)
        collection.load()
        logger.info(f"[Milvus] Collection '{collection_name}' initialized and loaded.")
        return collection

    @classmethod
    async def store_global_fact(cls, user_id: str, vector: List[float], metadata: Dict[str, Any]):
        """
        Sovereign v15.0: Distributed Cognitive Sync.
        Stores mission embeddings with mandatory flush for cross-region consistency.
        """
        if not cls.connect(): return
        
        try:
            collection = await cls.ensure_collection("sovereign_memory_global")
            import time
            data = [
                [user_id],
                [vector],
                [metadata],
                [int(time.time())]
            ]
            collection.insert(data)
            # v15.0 Mandatory Flush for immediate consistency
            collection.flush() 
            logger.debug(f"[Milvus] Global fact ARCHIVED and FLUSHED for {user_id}")
        except Exception as e:
            logger.error(f"[Milvus] Global storage failure: {e}")

    @classmethod
    async def search_global(cls, user_id: str, vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Performs a global semantic search across all system nodes."""
        if not cls.connect(): return []
        
        try:
            collection = await cls.ensure_collection("sovereign_memory_global")
            search_params = {"metric_type": "L2", "params": {"ef": 64}}
            
            results = collection.search(
                data=[vector], 
                anns_field="vector", 
                param=search_params, 
                limit=limit,
                expr=f"user_id == '{user_id}'",
                output_fields=["metadata", "timestamp"]
            )
            
            hits = []
            for hit in results[0]:
                hits.append({
                    "fact": hit.entity.get("metadata", {}).get("fact"),
                    "category": hit.entity.get("metadata", {}).get("category"),
                    "score": 1.0 - hit.distance, # Normalize L2 distance
                    "timestamp": hit.entity.get("timestamp")
                })
            return hits
        except Exception as e:
            logger.error(f"[Milvus] Global search failure: {e}")
            return []
