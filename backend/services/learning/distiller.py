"""
LEVI-AI Memory Distiller v13.0.0.
Sovereign OS production-grade "Dreaming Phase".
Consolidates episodic fragments into the Postgres SQL Fabric.
"""

import logging
import json
from datetime import datetime, timezone
from sqlalchemy import text
from backend.db.postgres_db import get_write_session
from backend.db.vector_store import VectorStoreV13
from backend.engines.chat.generation import SovereignGenerator
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class MemoryDistillerV13:
    """
    Sovereign Memory Distiller (v13.0.0).
    Identifies patterns in episodic fragments and consolidates them into the SQL Fabric.
    """

    async def distill_user_memory(self, user_id: str):
        """
        Dreaming Phase v13.0.0: Episodic -> SQL Crystallization.
        """
        logger.info(f"[Distiller-v13] Dreaming Phase initiated: {user_id}")
        
        # 1. Telemetry Pulse (v13.0)
        SovereignBroadcaster.broadcast({
            "type": "MEMORY_DREAMING_START",
            "message": "Analyzing episodic fragments...",
            "u": user_id
        })

        try:
            if len(fragments) < 3:
                # 2.1 Evolved Patterns & Successes (v14.1 Evolution Engine)
                pass # Continue to evolved patterns check

            evolved_data = []
            async with get_write_session() as session:
                # Fetch recent high-fidelity patterns
                stmt = text("SELECT query, result FROM training_corpus WHERE fidelity_score > 0.95 LIMIT 10")
                res = await session.execute(stmt)
                evolved_data = [f"{r['query']} -> {r['result'][:100]}" for r in res.mappings()]
            
            if not fragments and not evolved_data:
                return

            # 3. Swarm Appraisal (Council of Models)
            fact_block = "\n".join([f"- {f.get('text')}" for f in fragments])
            if evolved_data:
                fact_block += "\n\nEvolved Patterns:\n" + "\n".join([f"- {p}" for p in evolved_data])
            system_prompt = (
                "You are the LEVI Core Distiller (v13.0.0). "
                "Synthesize fragments into high-fidelity Identity Traits and Relational Triplets.\n"
                "Focus on philosophical patterns and long-term values.\n"
                "Output ONLY valid JSON: {\"traits\": [{\"text\": \"...\", \"weight\": 0.95}], \"triplets\": []}"
            )

            generator = SovereignGenerator()
            raw_res = await generator.council_of_models([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Fragments:\n{fact_block}"}
            ])

            # JSON Sanitization
            if "```json" in raw_res: raw_res = raw_res.split("```json")[-1].split("```")[0].strip()
            data = json.loads(raw_res)
            traits = data.get("traits", [])

            # 4. Global crystallization (SQL Fabric v13)
            async with get_write_session() as session:
                for t in traits:
                    if t.get("weight", 0) > 0.7:
                        await session.execute(
                            text("""
                                INSERT INTO user_traits (user_id, trait, weight, crystallized_at)
                                VALUES (:uid, :trait, :weight, :ts)
                                ON CONFLICT (user_id, trait) DO UPDATE SET weight = :weight, crystallized_at = :ts
                            """),
                            {
                                "uid": user_id,
                                "trait": t["text"],
                                "weight": t["weight"],
                                "ts": datetime.now(timezone.utc)
                            }
                        )

            logger.info(f"[Distiller-v13] Success: Crystallized {len(traits)} traits.")
            
            # 5. Final Synthesis Pulse
            SovereignBroadcaster.broadcast({
                "type": "MEMORY_DREAMING_COMPLETE",
                "count": len(traits),
                "u": user_id
            })

        except Exception as e:
            logger.error(f"[Distiller-v13] Distillation flux: {e}")
            SovereignBroadcaster.broadcast({"type": "MEMORY_DREAMING_ERROR", "error": str(e)})

# Singleton instance
distiller = MemoryDistillerV13()

# Versioned Alias for System Orchestration (v13.0)
MemoryDistiller = MemoryDistillerV13
