"""
Sovereign Database Orchestrator v8.
Central entry point for all database connections (Firestore, Redis, Mongo, Vector).
"""

import logging
import asyncio
from .firebase import get_db as get_firestore, get_auth as get_firebase_auth
from .redis import get_redis_client
from .mongo import MongoDB
from .postgres import PostgresDB
from .vector import get_vector_index

logger = logging.getLogger(__name__)

async def initialize_connections():
    """Wakes up all neural links for the Sovereign OS."""
    logger.info("Sovereign DB: Initializing core database links...")
    
    # 1. Firestore / Firebase
    firestore = get_firestore()
    if firestore: logger.info("Sovereign DB: Firestore link established.")
    
    # 2. Redis
    redis = get_redis_client()
    if redis: logger.info("Sovereign DB: Redis link established.")
    
    # 3. MongoDB (Prod Persistence)
    mongo = await MongoDB.get_db()
    if mongo is not None: logger.info("Sovereign DB: MongoDB link established.")

    # 4. Postgres (Mission-Critical Persistence)
    postgres = PostgresDB.get_engine()
    if postgres is not None: logger.info("Sovereign DB: Postgres link established.")
    
    logger.info("Sovereign DB: All links synchronized.")

async def close_connections():
    """Safely severs all neural links."""
    logger.info("Sovereign DB: Severing database links...")
    from .mongo import client as mongo_client
    if mongo_client: mongo_client.close()
    
    from .postgres import PostgresDB
    await PostgresDB.close()
    # Add other closers if needed
