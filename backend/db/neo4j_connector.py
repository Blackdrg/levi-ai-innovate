# neo4j_connector.py
from neo4j import AsyncGraphDatabase
import os
import logging

logger = logging.getLogger(__name__)

class Neo4jStore:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASS", "sovereign_graph")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self.driver.close()

    async def store_knowledge(self, subject: str, relation: str, obj: str):
        async with self.driver.session() as session:
            await session.run(
                "MERGE (a:Entity {name: $subject}) "
                "MERGE (b:Entity {name: $object}) "
                "MERGE (a)-[:RELATES {type: $relation}]->(b)",
                subject=subject, object=obj, relation=relation
            )

    async def query_related(self, subject: str) -> list:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (a:Entity {name: $subject})-[r]->(b) "
                "RETURN b.name as name, type(r) as relation",
                subject=subject
            )
            return [record.data() async for record in result]
