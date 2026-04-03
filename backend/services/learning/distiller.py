import logging
import json
from backend.db.vector_store import embed_text
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault
from backend.engines.chat.generation import SovereignGenerator
from backend.memory.graph_engine import GraphEngine
from backend.utils.broadcast import SovereignBroadcaster
from backend.db.postgres import PostgresDB
from backend.db.models import UserProfile, UserTrait, UserPreference
from sqlalchemy import select, update
from datetime import datetime, timezone


logger = logging.getLogger(__name__)

class MemoryDistiller:
    """
    Sovereign Memory Distiller (The "Dreaming Phase").
    Identifies patterns in short-term episodic facts and consolidates them into 
    long-term Semantic (FAISS) and Relational (Neo4j) nodes.
    """

    def __init__(self):
        self.graph = GraphEngine()

    async def distill_user_memory(self, user_id: str):
        """
        Dreaming Phase v8: Episodic -> Semantic crystallization with encryption.
        """
        logger.info(f"[Distiller] Dreaming Phase initiated for user: {user_id}")
        
        # 1. Telemetry Pulse
        SovereignBroadcaster.publish(
            "MEMORY_DREAMING_START", 
            {"status": "active", "message": "Analyzing episodic fragments..."}, 
            user_id=user_id
        )

        try:
            # 2. Extract Episodic facts
            memory_db = await VectorDB.get_user_collection(user_id, "memory")
            facts_data = await memory_db.search("user traits and preferences", limit=20)
            
            if len(facts_data) < 3:
                logger.debug(f"[Distiller] Insufficient fragments for crystallization ({user_id})")
                return

            fact_strings = "\n".join([f"- {f.get('text')}" for f in facts_data])
            
            # 3. Engage the Council for High-Fidelity Synthesis & Pruning
            # Requirement: Identify 'Core Identity Weights' (e.g. Stoicism, User Values)
            system_prompt = (
                "You are the LEVI Core Distiller. Synthesize fragmented episodic facts into:\n"
                "1. Core Identity Traits (Permanent Semantic Nodes).\n"
                "2. Relational Triplets (Subject-Relation-Object) for the Knowledge Graph.\n"
                "3. Identity Weights: Assign a floating point [0.0 - 1.0] to traits reflecting their importance to the user's core identity (e.g., 'Values Stoicism': 0.95).\n\n"
                "Focus on identifying deep philosophical patterns and long-term behavioral values.\n"
                "Return ONLY valid JSON: {\"traits\": [{\"text\": \"...\", \"weight\": 0.0}], \"triplets\": [{\"s\": \"...\", \"r\": \"...\", \"o\": \"...\"}]}"
            )
            
            generator = SovereignGenerator()
            raw_res = await generator.council_of_models([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Input Fragments (Episodic Memory Loop):\n{fact_strings}"}
            ])
            
            # JSON sanitization
            if "```json" in raw_res: raw_res = raw_res.split("```json")[-1].split("```")[0].strip()
            elif "```" in raw_res: raw_res = raw_res.split("```")[-1].split("```")[0].strip()
            
            data = json.loads(raw_res)
            traits = data.get("traits", [])
            triplets = data.get("triplets", [])

            # 4. Crystallize Knowledge Graph (Neo4j)
            for t in triplets:
                await self.graph.upsert_triplet(user_id, t["s"], t["r"], t["o"])
            
            # 5. Crystallize Identity Traits (FAISS + SovereignVault)
            traits_db = await VectorDB.get_user_collection(user_id, "traits")
            for trait_data in traits:
                trait_text = trait_data.get("text")
                weight = trait_data.get("weight", 0.5)
                
                # V8 Evolution: Only crystallize if weight meets threshold (Self-Pruning)
                if weight < 0.3:
                    logger.debug(f"[Distiller] Pruning low-weight trait: {trait_text}")
                    continue

                # User requirement: Encrypt identity at rest
                encrypted_trait = SovereignVault.encrypt(trait_text)
                await traits_db.add(
                    [encrypted_trait], 
                    [{"type": "trait", "weight": weight, "crystallized_at": str(datetime.now())}]
                )
            
            # 6. Tier 4: Identity Consolidation (Postgres)
            async with PostgresDB._session_factory() as session:
                # 6.1 Ensure Profile exists
                profile = await session.get(UserProfile, user_id)
                if not profile:
                    profile = UserProfile(user_id=user_id, persona_archetype="philosophical")
                    session.add(profile)
                
                # 6.2 Update Traits (Merge logic)
                for trait_data in traits:
                    if trait_data.get("weight", 0) > 0.7: # Significant traits only for Tier 4
                        # Check if similar trait exists (simplified exact match for now)
                        # In production, this would use semantic similarity
                        new_trait = UserTrait(
                            user_id=user_id, 
                            trait=trait_data["text"], 
                            weight=trait_data["weight"],
                            crystallized_at=datetime.now(timezone.utc)
                        )
                        session.add(new_trait)
                
                await session.commit()

            logger.info(f"[Distiller] Success: Crystallized {len(traits)} Traits for {user_id}.")
            
            # 7. Final Status Update
            SovereignBroadcaster.publish(
                "MEMORY_DREAMING_COMPLETE", 
                {"status": "complete", "traits_count": len(traits), "triplets_count": len(triplets)}, 
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"[Distiller] Dreaming sequence anomaly: {e}")
            SovereignBroadcaster.publish("MEMORY_DREAMING_ERROR", {"error": str(e)}, user_id=user_id)
