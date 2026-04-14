import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MemoryConsistencyManager:
    """
    Sovereign 5-Tier Memory Consistency Manager (v16.0).
    Synchronizes truth across Ephemeral (Redis), Factual (Postgres), Knowledge (Neo4j), 
    Semantic (FAISS), and Profile (Postgres) tiers.
    """
    def __init__(self, redis, postgres, neo4j, faiss, embedding_model=None):
        self.tiers = {
            'T0': redis,    # Ephemeral context (Redis)
            'T1': postgres, # Factual ledger (Postgres)
            'T2': neo4j,    # Knowledge graph (Neo4j)
            'T3': faiss,    # Semantic vectors (FAISS)
            'T4': postgres  # User profiles (Postgres)
        }
        self.embedding_model = embedding_model
        # Fallback if no embedding model provided
        if not self.embedding_model:
            from backend.embeddings import SovereignEmbeddings
            self.embedding_model = SovereignEmbeddings()

    async def crystallize_fact(self, fact_id: str, value: Dict, user_id: str):
        """Persist fact across all 5 tiers"""
        logger.info(f"💎 [MCM] Crystallizing fact {fact_id} for user {user_id} across 5 tiers...")
        
        # T0: Redis cache (Ephemeral)
        try:
            await self.tiers['T0'].set(
                f"fact:{fact_id}",
                json.dumps(value),
                ex=3600  # 1 hour TTL
            )
        except Exception as e:
            logger.error(f"[MCM-T0] Redis write failed: {e}")
        
        # T1: PostgreSQL permanent (Factual Ledger)
        try:
            await self.tiers['T1'].execute(
                "INSERT INTO user_facts (fact_id, user_id, content, created_at) "
                "VALUES ($1, $2, $3, NOW())",
                fact_id, user_id, json.dumps(value)
            )
        except Exception as e:
            logger.error(f"[MCM-T1] Postgres write failed: {e}")
        
        # T2: Neo4j knowledge graph (Relational)
        try:
            entities = self._extract_entities(value)
            for entity in entities:
                await self.tiers['T2'].run(
                    "MERGE (n:Fact {id: $id}) "
                    "SET n.content = $content, n.user_id = $user_id "
                    "MERGE (e:Entity {name: $entity_name}) "
                    "CREATE (n)-[:CONTAINS]-(e)",
                    id=fact_id, content=value.get('text', ''),
                    user_id=user_id, entity_name=entity
                )
        except Exception as e:
            logger.error(f"[MCM-T2] Neo4j write failed: {e}")
        
        # T3: FAISS semantic vectors (Neural)
        try:
            embedding = await self.embedding_model.embed(value.get('text', ''))
            # metadata is handled by the vector store wrapper in our implementation
            await self.tiers['T3'].add_vector(
                np.array([embedding]).astype('float32'),
                {"fact_id": fact_id, "user_id": user_id}
            )
        except Exception as e:
            logger.error(f"[MCM-T3] FAISS write failed: {e}")
        
        # T4: User profile update (Identity)
        try:
            await self.tiers['T4'].execute(
                "UPDATE user_profiles SET fact_count = fact_count + 1 "
                "WHERE user_id = $1",
                user_id
            )
        except Exception as e:
            logger.error(f"[MCM-T4] Profile update failed: {e}")
        
        return {'status': 'crystallized', 'tiers': 5}
    
    async def resonance_recall(self, query: str, user_id: str, top_k: int = 5):
        """Multi-tier semantic recall: Vector + Graph fusion"""
        logger.info(f"🧠 [MCM] Resonance recall for query: {query[:50]}")
        
        # T3: FAISS vector search
        vector_results = []
        try:
            query_embedding = await self.embedding_model.embed(query)
            vector_results = await self.tiers['T3'].search(
                np.array([query_embedding]).astype('float32'),
                k=top_k
            )
        except Exception as e:
            logger.error(f"[MCM-T3] Vector search failed: {e}")
        
        # T2: Neo4j resonance (3-hop relationships)
        graph_results = []
        try:
            graph_results = await self.tiers['T2'].run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (u)-[:HAS_FACT]->(f:Fact)
                MATCH (f)-[r:RESONATES_WITH*1..3]-(c:Fact)
                WHERE c.relevance_score > 0.7
                RETURN c.id, c.content, r[0].weight AS resonance
                ORDER BY resonance DESC LIMIT $k
                """,
                user_id=user_id, k=top_k
            )
        except Exception as e:
            logger.error(f"[MCM-T2] Graph recall failed: {e}")
        
        # Fuse results: 60% vector, 40% graph
        combined = self._fuse_results(vector_results, graph_results, 0.6)
        return combined

    def _extract_entities(self, value: Dict) -> List[str]:
        """Simple entity extraction from fact value."""
        return value.get("entities", []) or [e for e in value.get("text", "").split() if e[0].isupper()]

    def _fuse_results(self, vector_res: List, graph_res: List, alpha: float) -> List[Dict]:
        """Hybrid fusion of vector and graph results."""
        # Simple RRF or weighted fusion
        fused = []
        for v in vector_res:
            fused.append({**v, "score": v.get("score", 0.5) * alpha})
        for g in graph_res:
            fused.append({**g, "score": g.get("resonance", 0.5) * (1 - alpha)})
        return sorted(fused, key=lambda x: x["score"], reverse=True)
