from neo4j import GraphDatabase
import os

class Neo4jStore:
    def __init__(self):
        # 3 lines of config for Bolt Driver
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "sovereign_graph"))
        self.driver = GraphDatabase.driver(uri, auth=auth)
    
    def close(self):
        self.driver.close()

    async def store_knowledge(self, source, relation, target):
        """
        Sovereign v13: Episodic Knowledge Graph writing.
        """
        def _write(tx, s, r, t):
            query = (
                "MERGE (a:Entity {name: $s}) "
                "MERGE (b:Entity {name: $t}) "
                f"MERGE (a)-[:{r}]->(b)"
            )
            tx.run(query, s=s, t=t)

        with self.driver.session() as session:
            session.execute_write(_write, source, relation, target)
