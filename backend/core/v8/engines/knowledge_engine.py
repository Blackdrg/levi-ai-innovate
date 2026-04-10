import logging
from typing import Dict, Any, Optional
from backend.db.neo4j_db import execute_query

logger = logging.getLogger(__name__)

class KnowledgeEngine:
    """
    Knowledge Graph Engine (v8.15)
    Executes Cypher queries directly against the Neo4j Graph Database.
    """

    def __init__(self, driver=None):
        self.driver = driver

    async def run(self, cypher: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Executes a Cypher query and returns the results with safety validation.
        """
        from backend.utils.security import CypherProtector
        
        if not CypherProtector.validate_query(cypher, parameters):
             return {
                 "success": False, 
                 "error": "Security Shield Triggered: Unauthorized Cypher execution attempted.",
                 "engine": "knowledge"
             }

        try:
            logger.info(f"[KnowledgeEngine] Executing Hardened Cypher query: {cypher[:50]}...")
            
            # If no driver is provided, use the global execute_query utility
            results = await execute_query(cypher, parameters)
            
            return {
                "success": True,
                "data": results,
                "engine": "knowledge",
                "message": f"Graph query executed. {len(results)} records found."
            }
        except Exception as e:
            logger.error(f"[KnowledgeEngine] Query failure: {e}")
            return {"success": False, "error": str(e), "engine": "knowledge"}

    async def query(self, cypher: str):
        """Legacy sync-style wrapper for compatibility if needed."""
        res = await self.run(cypher)
        return res.get("data", [])
