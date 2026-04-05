import os
import asyncio
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

async def test_neo4j():
    # Credentials from docker-compose.yml line 56
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = "neo4j"
    password = "sovereign_graph" # Correct password from your config
    
    print(f"--- Testing Neo4j Connection at {uri} ---")
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        await driver.verify_connectivity()
        print("✅ Neo4j Connection SUCCESS!")
        return True
    except Exception as e:
        print(f"❌ Neo4j Connection FAILED: {str(e)}")
        print("\n💡 TIP: Ensure you ran 'docker compose up -d' and wait 30s for start-up.")
        return False
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(test_neo4j())
