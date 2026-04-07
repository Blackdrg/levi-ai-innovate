import pytest
from backend.db.mongo import MongoDB

@pytest.mark.asyncio
async def test_mongodb_connection():
    # This test assumes a MONGODB_URI is provided in the environment or .env.local
    db = await MongoDB.get_db()
    if db is not None:
        # Test basic write/read
        test_collection = db.test_collection
        test_data = {"test": "data", "service": "brain"}
        result = await test_collection.insert_one(test_data)
        assert result.inserted_id is not None
        
        found = await test_collection.find_one({"_id": result.inserted_id})
        assert found["test"] == "data"
        
        # Cleanup
        await test_collection.delete_one({"_id": result.inserted_id})
    else:
        pytest.skip("MongoDB URI not configured, skipping persistence test.")

@pytest.mark.asyncio
async def test_fact_storage_backup():
    from backend.services.orchestrator.memory_utils import store_facts
    import uuid
    
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    new_facts = [{"fact": "The user likes coffee", "category": "preference"}]
    
    # This will trigger the background task to backup to MongoDB
    await store_facts(user_id, new_facts)
    
    db = await MongoDB.get_db()
    if db is not None:
        # Wait a bit for the async task
        import asyncio
        await asyncio.sleep(1)
        
        found = await db.user_facts.find_one({"user_id": user_id})
        assert found is not None
        assert found["fact"] == "The user likes coffee"
        
        # Cleanup
        await db.user_facts.delete_many({"user_id": user_id})
    else:
        pytest.skip("MongoDB URI not configured.")

@pytest.fixture(scope="session", autouse=True)
async def cleanup_mongo():
    yield
    await MongoDB.close()
