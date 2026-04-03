import asyncio
import os
import logging
import asyncpg
import motor.motor_asyncio
import aioredis
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_v8_sovereign_infra():
    """
    LeviBrain v8: High-Fidelity Infrastructure Verification.
    Diagnoses connectivity to all 4 cognitive stores.
    """
    print("\n--- INITIATING LEVIBRAIN V8 INFRASTRUCTURE DIAGNOSTIC ---\n")
    
    # 1. Postgres Verification (Identity & Mission Store)
    try:
        database_url = os.getenv("DATABASE_URL", "postgresql://levi:levi_pass@localhost:5432/levidb")
        conn = await asyncpg.connect(database_url)
        print("[1/4] POSTGRES: Sovereign Mission Store is ONLINE.")
        await conn.close()
    except Exception as e:
        print(f"[1/4] POSTGRES: FAILURE - {e}")
        
    # 2. Redis Verification (Context & State Store)
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = await aioredis.from_url(redis_url)
        await redis.ping()
        print("[2/4] REDIS: Sovereign Context State is ONLINE.")
    except Exception as e:
        print(f"[2/4] REDIS: FAILURE - {e}")

    # 3. Kafka Verification (Learning & Event Bus)
    try:
        kafka_url = os.getenv("KAFKA_URL", "localhost:9092")
        producer = AIOKafkaProducer(bootstrap_servers=kafka_url)
        await producer.start()
        print("[3/4] KAFKA: Sovereign Event Bus is ONLINE.")
        await producer.stop()
    except Exception as e:
        print(f"[3/4] KAFKA: FAILURE - {e}")
        
    # 4. MongoDB Verification (Long-Term Semantic Vault)
    try:
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
        await client.admin.command('ping')
        print("[4/4] MONGODB: Sovereign Semantic Vault is ONLINE.")
    except Exception as e:
        print(f"[4/4] MONGODB: FAILURE - {e}")

    print("\n--- V8 INFRASTRUCTURE DIAGNOSTIC COMPLETE ---\n")

if __name__ == "__main__":
    asyncio.run(verify_v8_sovereign_infra())
