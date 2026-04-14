import pytest
import asyncio
from unittest.mock import MagicMock
from backend.memory.mcm_service import MemoryConsistencyManager

@pytest.mark.asyncio
async def test_all_5_tiers_sync():
    # Mock tiers
    redis = MagicMock()
    postgres = MagicMock()
    neo4j = MagicMock()
    faiss = MagicMock()
    
    # Mock async methods
    redis.set = MagicMock(return_value=asyncio.Future())
    redis.set.return_value.set_result(True)
    
    postgres.execute = MagicMock(return_value=asyncio.Future())
    postgres.execute.return_value.set_result(True)
    
    neo4j.run = MagicMock(return_value=asyncio.Future())
    neo4j.run.return_value.set_result(True)
    
    faiss.add_vector = MagicMock(return_value=asyncio.Future())
    faiss.add_vector.return_value.set_result(True)
    
    # Mock embedding model
    embedding_model = MagicMock()
    embedding_model.embed = MagicMock(return_value=asyncio.Future())
    embedding_model.embed.return_value.set_result([0.1, 0.2, 0.3])

    mcm = MemoryConsistencyManager(redis, postgres, neo4j, faiss, embedding_model=embedding_model)
    
    fact = {
        'text': 'LEVI-AI uses sovereign inference',
        'importance': 0.95,
        'entities': ['LEVI-AI', 'sovereign', 'inference']
    }
    
    result = await mcm.crystallize_fact('f_001', fact, 'user_123')
    assert result['tiers'] == 5
    
    # Verify calls
    redis.set.assert_called_once()
    assert postgres.execute.call_count == 2 # T1 and T4
    neo4j.run.assert_called()
    faiss.add_vector.assert_called_once()
