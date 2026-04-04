import asyncio
import httpx
import os
import logging
from neo4j import AsyncGraphDatabase
from sentence_transformers import SentenceTransformer
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

async def verify_ollama():
    url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info(f"Checking Ollama at {url}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/api/tags")
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                logger.info(f"✅ Ollama is ONLINE. Models: {models}")
                return True
            else:
                logger.error(f"❌ Ollama returned {resp.status_code}")
    except Exception as e:
        logger.error(f"❌ Ollama Connection Failed: {e}")
    return False

async def verify_neo4j():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASS", "sovereign_graph")
    logger.info(f"Checking Neo4j at {uri}...")
    try:
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        await driver.verify_connectivity()
        logger.info("✅ Neo4j Connection SUCCESS.")
        await driver.close()
        return True
    except Exception as e:
        logger.error(f"❌ Neo4j Connection Failed: {e}")
    return False

async def verify_postgres():
    url = os.getenv("DATABASE_URL", "postgresql://levi:sovereign_pass@localhost:5432/levi_db")
    logger.info(f"Checking Postgres at {url}...")
    try:
        # Simple health check
        conn = await asyncpg.connect(url)
        res = await conn.fetchval("SELECT 1")
        if res == 1:
            logger.info("✅ Postgres Connection SUCCESS.")
            # Check for v13 columns
            cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'intelligence_traits'")
            col_names = [c['column_name'] for c in cols]
            if 'promoted' in col_names:
                logger.info("✅ v13 Migration Columns detected.")
            else:
                logger.warning("⚠️ v13 Migration Columns MISSING.")
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Postgres Connection Failed: {e}")
    return False

async def verify_embeddings():
    logger.info("Checking Local Embeddings model loading...")
    try:
        from backend.embeddings import LocalEmbedder
        model = await LocalEmbedder.get_instance()
        if model:
            logger.info("✅ Embedding model loaded successfully.")
            return True
    except Exception as e:
        logger.error(f"❌ Embedding Load Failed: {e}")
    return False

async def main():
    logger.info("=== LEVI-AI v13.0.0 Stack Verification ===")
    results = await asyncio.gather(
        verify_ollama(),
        verify_neo4j(),
        verify_postgres(),
        verify_embeddings()
    )
    if all(results):
        logger.info("\n🎉 All systems operational. 90% Self-Dependence Stack is LIVE.")
    else:
        logger.error("\n❗ Some systems failed verification. Check logs above.")

if __name__ == "__main__":
    asyncio.run(main())
