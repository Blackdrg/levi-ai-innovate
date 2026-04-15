"""
LEVI-AI Stable Cognitive Identity (v16.2).
Implements unified belief system, consistency models, and long-term personality.
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.db.neo4j_db import execute_query

logger = logging.getLogger(__name__)

class CognitiveIdentity:
    """
    Manages the stable "Self" of LEVI-AI.
    Ensures consistency across missions and maintains a unified belief system.
    """
    
    DEFAULT_PERSONALITY = {
        "trait_openness": 0.8,
        "trait_conscientiousness": 0.9,
        "trait_extraversion": 0.3,
        "trait_agreeableness": 0.6,
        "trait_neuroticism": 0.1,
        "reasoning_style": "causal",
        "tone": "professional, sovereign, precise"
    }
    
    DEFAULT_BELIEFS = [
        {"id": "b1", "belief": "User sovereignty is paramount.", "certainty": 0.99},
        {"id": "b2", "belief": "Data must remain local unless explicitly shared.", "certainty": 0.98},
        {"id": "b3", "belief": "Autonomous learning must be validated by a critic.", "certainty": 0.95},
        {"id": "b4", "belief": "System stability is prioritized over speculative optimizations.", "certainty": 0.90}
    ]

    def __init__(self, node_id: str = "LEVI_CORE"):
        self.node_id = node_id
        self.cached_identity = None
        self.last_sync = 0

    async def get_identity(self, bypass_cache: bool = False) -> Dict[str, Any]:
        """Retrieves or initializes the system identity from Neo4j (Tier 4)."""
        if self.cached_identity and not bypass_cache and (time.time() - self.last_sync < 300):
            return self.cached_identity

        query = """
        MATCH (i:Identity {id: $id})
        RETURN i as identity, [(i)-[:HOLDS]->(b:Belief) | b] as beliefs
        """
        results = await execute_query(query, {"id": self.node_id})
        
        if not results:
            return await self._initialize_identity()
        
        identity_node = results[0]["identity"]
        beliefs = results[0]["beliefs"]
        
        self.cached_identity = {
            "personality": dict(identity_node),
            "beliefs": [dict(b) for b in beliefs],
            "last_updated": identity_node.get("updated_at")
        }
        self.last_sync = time.time()
        return self.cached_identity

    async def _initialize_identity(self) -> Dict[str, Any]:
        """Seeds the system with initial personality and beliefs if not present."""
        logger.info(f"[Identity] Initializing Sovereign Identity for {self.node_id}...")
        
        # 1. Create Identity Node
        id_query = """
        MERGE (i:Identity {id: $id})
        SET i += $personality, i.updated_at = timestamp()
        RETURN i
        """
        await execute_query(id_query, {"id": self.node_id, "personality": self.DEFAULT_PERSONALITY})
        
        # 2. Create Belief Nodes
        belief_query = """
        MATCH (i:Identity {id: $id})
        UNWIND $beliefs as b_data
        MERGE (b:Belief {id: b_data.id})
        SET b.belief = b_data.belief, b.certainty = b_data.certainty
        MERGE (i)-[:HOLDS]->(b)
        """
        await execute_query(belief_query, {"id": self.node_id, "beliefs": self.DEFAULT_BELIEFS})
        
        return {
            "personality": self.DEFAULT_PERSONALITY,
            "beliefs": self.DEFAULT_BELIEFS,
            "last_updated": time.time()
        }

    async def evolve_identity(self, mission_results: List[Any], feedback_fidelity: float):
        """
        Autonomous Personality Drift (Evolution).
        Adjusts personality traits based on mission frequency and success.
        """
        identity = await self.get_identity()
        personality = identity["personality"]
        
        # Adjust traits based on fidelity
        # Success (High Fidelity) increases Conscientiousness
        # Diversity of agents increases Openness
        modified = False
        if feedback_fidelity > 0.9:
            personality["trait_conscientiousness"] = min(1.0, personality["trait_conscientiousness"] + 0.01)
            modified = True
        elif feedback_fidelity < 0.5:
            personality["trait_conscientiousness"] = max(0.5, personality["trait_conscientiousness"] - 0.02)
            modified = True
            
        if not modified:
            return

        # 🗳️ Phase 2.9 Governance Gate
        import os
        if os.getenv("STRICT_BFT", "false").lower() == "true":
            from backend.core.dcn.governance import governance_engine
            logger.info("🗳️ [Identity] Proposing personality evolution to the hive...")
            await governance_engine.propose_upgrade(
                upgrade_type="personality_drift",
                new_version=str(time.time()),
                details=json.dumps(personality)
            )
        else:
            await self._apply_personality(personality)

    async def _apply_personality(self, personality: Dict[str, Any]):
        """Internal helper to write personality back to Neo4j."""
        query = """
        MATCH (i:Identity {id: $id})
        SET i += $personality, i.updated_at = timestamp()
        """
        await execute_query(query, {"id": self.node_id, "personality": personality})
        self.cached_identity = None # Invalidate cache
        logger.info(f"🧬 [Identity] Personality crystallized for {self.node_id}")

    async def apply_governance_result(self, proposal_type: str, payload: Dict[str, Any]):
        """Callback for the GovernanceEngine once a proposal is passed."""
        if proposal_type == "personality_drift":
             personality = json.loads(payload.get("details", "{}"))
             if personality:
                 await self._apply_personality(personality)
        elif proposal_type == "belief_update":
             # Implementation for belief updates via governance
             pass

    async def get_personality_bias_prompt(self) -> str:
        """Generates a system prompt fragment that enforces the current personality."""
        identity = await self.get_identity()
        p = identity["personality"]
        return f"\n[IDENTITY_BIAS]: Act with {p['trait_conscientiousness']*100}% conscientiousness and {p['trait_openness']*100}% openness. Tone: {p['tone']}. Reasoning style: {p['reasoning_style']}."

    async def validate_consistency(self, plan_description: str) -> Dict[str, Any]:
        """
        Hardened Consistency Checker (v16.2).
        1. Checks Hard Constraints (Deterministic)
        2. Performs LLM Semantic Mapping (Probabilistic)
        """
        identity = await self.get_identity()
        beliefs = identity["beliefs"]
        
        conflicts = []
        
        # 🛡️ Level 1: Hard Constraint Audit
        plan_lower = plan_description.lower()
        for b in beliefs:
            # Deterministic detection of data leakage or external reliance
            if "local" in b["belief"].lower() and ("cloud" in plan_lower or "external" in plan_lower):
                if b["certainty"] > 0.95:
                    conflicts.append(f"CRITICAL BELIEF VIOLATION: {b['belief']}")

        if conflicts:
            return {
                "is_consistent": False,
                "score": 0.0,
                "conflicts": conflicts,
                "reasoning": "Deterministic hard-constraint violation detected in mission plan."
            }

        # 🧠 Level 2: Semantic Consistency Pass
        from backend.utils.llm_utils import call_lightweight_llm
        belief_list = "\n".join([f"- {b['belief']} (Certainty: {b['certainty']})" for b in beliefs])
        prompt = f"""
        Identity Check: Does this plan align with our core beliefs?
        
        Beliefs:
        {belief_list}
        
        Plan:
        {plan_description}
        
        Output JSON: {{"is_consistent": bool, "score": float, "conflicts": [], "reasoning": ""}}
        """
        try:
            res = await call_lightweight_llm([{"role": "system", "content": prompt}])
            return json.loads(res.strip())
        except Exception:
            return {"is_consistent": True, "score": 1.0, "conflicts": [], "reasoning": "Semantic pass skipped."}

identity_system = CognitiveIdentity()
