"""
LEVI-AI Sovereign OS v8 - DB Tier Unified Tests.
Validates the central Redis and Firebase interfaces.
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.db.redis import get_redis_client, distributed_lock
from backend.db.firebase import db as firestore_db

@pytest.mark.asyncio
async def test_redis_connection():
    """Verify Redis client is a singleton and responsive."""
    with patch('backend.db.redis.r') as mock_redis:
        client = get_redis_client()
        client.ping()
        mock_redis.ping.assert_called_once()

@pytest.mark.asyncio
async def test_distributed_lock_success():
    """Verify the atomic lock acquisition logic."""
    with patch('backend.db.redis.r') as mock_redis:
        mock_redis.set.return_value = True # Successful lock
        
        with distributed_lock("test_lock", ttl=5) as acquired:
            assert acquired is True
            
        mock_redis.delete.assert_called_with("lock:test_lock")

@pytest.mark.asyncio
async def test_firebase_logic():
    """Verify Firestore interface mapping."""
    with patch('backend.db.firebase.db') as mock_fb:
        # Test basic collection access
        firestore_db.collection("users")
        mock_fb.collection.assert_called_with("users")
