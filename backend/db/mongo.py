import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDB:
    _client: Optional[AsyncIOMotorClient] = None
    _db = None

    @classmethod
    async def get_db(cls):
        if cls._db is None:
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                logger.warning("MONGODB_URI not found in environment. Memory engine will be degraded.")
                return None
            
            try:
                cls._client = AsyncIOMotorClient(mongo_uri)
                db_name = os.getenv("MONGODB_DB_NAME", "levi_ai")
                cls._db = cls._client[db_name]
                logger.info(f"Connected to MongoDB Atlas: {db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                return None
        return cls._db

    @classmethod
    async def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("MongoDB connection closed.")

# Dependency for FastAPI
async def get_mongodb():
    return await MongoDB.get_db()
