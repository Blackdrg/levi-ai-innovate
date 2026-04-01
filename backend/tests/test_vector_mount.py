import pytest
import os
import json
import faiss  # type: ignore
from backend.utils.vector_db import VectorDB

@pytest.mark.asyncio
async def test_vector_db_path_config():
    """Verify that VECTOR_DB_PATH environment variable is respected."""
    custom_path = "/tmp/test_vector_db"
    os.environ["VECTOR_DB_PATH"] = custom_path
    
    db = await VectorDB.get_collection("test_mount")
    assert db.base_path == custom_path
    assert os.path.exists(custom_path)
    
    # Cleanup env
    del os.environ["VECTOR_DB_PATH"]

@pytest.mark.asyncio
async def test_atomic_save_and_persistence():
    """Verify that FAISS indices are saved correctly using the atomic replacement strategy."""
    custom_path = "/tmp/test_persistence"
    os.makedirs(custom_path, exist_ok=True)
    os.environ["VECTOR_DB_PATH"] = custom_path
    
    db = await VectorDB.get_collection("persist_test", dimension=384)
    
    texts = ["LEVI is a production-grade AI.", "Scaling is handled by Cloud Run."]
    metadatas = [{"source": "test"}, {"source": "test"}]
    
    await db.add(texts, metadatas)
    
    # Check if files exist
    assert os.path.exists(os.path.join(custom_path, "persist_test_faiss.bin"))
    assert os.path.exists(os.path.join(custom_path, "persist_test_meta.json"))
    
    # Check if .tmp files are cleaned up
    assert not os.path.exists(os.path.join(custom_path, "persist_test_faiss.bin.tmp"))
    
    # Verify content after reload
    VectorDB._instances.pop("persist_test", None)
    new_db = await VectorDB.get_collection("persist_test", dimension=384)
    results = await new_db.search("LEVI AI", limit=1)
    
    assert len(results) > 0
    assert "production-grade" in results[0]["text"]
    
    # Cleanup
    import shutil
    shutil.rmtree(custom_path)
    del os.environ["VECTOR_DB_PATH"]
