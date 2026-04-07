"""
Sovereign Rules Engine v13.0.0.
High-fidelity reinforcement learning and pattern distillation.
Synchronized with the Absolute Monolith SQL Fabric.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from backend.db.postgres_db import get_read_session, get_write_session
from backend.memory.vector_store import SovereignVectorStore

logger = logging.getLogger(__name__)

class RulesEngine:
    """
    Sovereign Rules Engine v13.0.0.
    Manages deterministic rules promoted from autonomous evolution cycles.
    """

    async def get_rule(self, task_description: str, threshold: float = 0.95) -> Optional[str]:
        """
        Returns a crystallized solution from the Monolith SQL Fabric or HNSW Vault.
        """
        task_key = task_description.lower().strip()
        
        # 1. SQL Identity Match (High-Fidelity)
        try:
            async with get_read_session() as session:
                res = await session.execute(
                    text("SELECT result_data FROM sovereign_rules WHERE task_pattern = :pattern"),
                    {"pattern": task_key}
                )
                rule = res.mappings().one_or_none()
                if rule:
                    logger.info(f"[Rules-v13] SQL resonance found for: {task_key[:30]}...")
                    return rule["result_data"].get("solution")
        except Exception as e:
            logger.error(f"[Rules-v13] SQL lookup failed: {e}")

        # 2. HNSW Fuzzy Match
        try:
            search_results = await SovereignVectorStore.search_memories(
                user_id="system_rules",
                query=task_description,
                limit=1,
                category="rule"
            )
            
            if search_results and search_results[0].get("score", 0) >= threshold:
                content = search_results[0]["content"]
                if "response is '" in content:
                    solution = content.split("response is '")[-1].rstrip("'")
                    logger.info(f"[Rules-v13] HNSW fuzzy match found (Score: {search_results[0]['score']:.2f})")
                    return solution
        except Exception as e:
            logger.error(f"[Rules-v13] HNSW match failed: {e}")

        return None

    async def create_rule(self, task_description: str, solution: str, fidelity: float = 1.0):
        """
        Promotes a new deterministic rule to the Monolith SQL Fabric and HNSW Vault.
        """
        task_key = task_description.lower().strip()
        
        # 1. SQL Absolute Persistence
        try:
            async with get_write_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO sovereign_rules (task_pattern, result_data, fidelity_score, is_promoted)
                        VALUES (:pattern, :data, :fidelity, TRUE)
                        ON CONFLICT (task_pattern) DO UPDATE SET
                        result_data = EXCLUDED.result_data,
                        fidelity_score = EXCLUDED.fidelity_score
                    """),
                    {
                        "pattern": task_key,
                        "data": json.dumps({"solution": solution}),
                        "fidelity": fidelity
                    }
                )
        except Exception as e:
            logger.error(f"[Rules-v13] SQL promotion failed: {e}")
            raise

        # 2. HNSW Semantic Storage
        await SovereignVectorStore.store_fact(
            user_id="system_rules",
            fact=f"Deterministic Rule: If input is '{task_description}', response is '{solution}'",
            category="rule",
            importance=fidelity
        )
        
        logger.info(f"[Rules-v13] Rule promoted to Monolith for: {task_key[:50]}...")

    async def list_rules(self) -> List[Dict[str, Any]]:
        """ Lists all promoted rules from the SQL fabric. """
        async with get_read_session() as session:
            res = await session.execute(text("SELECT task_pattern, fidelity_score FROM sovereign_rules"))
            return [dict(row) for row in res.mappings()]
