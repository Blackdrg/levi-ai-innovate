import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from backend.core.orchestrator_types import IntentResult
from backend.memory.manager import MemoryManager
from .evolution_engine import EvolutionEngine
from .learning import FragilityTracker

logger = logging.getLogger(__name__)

class DecisionEngine:
    """
    LeviBrain v8.15: Hardened Decision Engine.
    Computes deterministic metrics to prioritize Brain-first execution.
    """

    def __init__(self):
        self.math_patterns = [
            r"^\s*[\d\.\+\-\*\/\(\)\^ \t]+\s*[=|\?]?\s*$", # Simple expressions
            r"\b(calculate|solve|what is|compute)\b.*\b([\d\.\+\-\*\/\^]+)\b",
            r"(sin|cos|tan|log|sqrt)\(.*\)"
        ]
        self.stats_keywords = ["sum", "avg", "average", "min", "max", "count", "mean", "median", "sort", "length"]
        self.evolution_engine = EvolutionEngine()

    def _get_agent_reward(self, agent_name: str) -> float:
        """Fetches the average reinforcement reward for an agent from Redis (v12.0)."""
        from backend.db.redis import r as redis_client, HAS_REDIS
        if not HAS_REDIS or not agent_name:
            return 0.0
            
        key = f"reinforcement:path:{agent_name}"
        try:
            rewards = redis_client.lrange(key, 0, 9) # Get last 10 trials
            if not rewards: return 1.0 # Default high for new/untested agents
            
            float_rewards = [float(r) for r in rewards]
            return sum(float_rewards) / len(float_rewards)
        except Exception:
            return 0.0

    def is_abstract_query(self, text: str) -> bool:
        """
        Detects philosophical, open-ended, or high-concept reasoning tasks.
        These require the full neural depth of an LLM.
        """
        abstract_keywords = [
            "meaning", "purpose", "why", "explain", "philosophy",
            "opinion", "thoughts", "life", "consciousness", "existential"
        ]
        return any(word in text.lower() for word in abstract_keywords)

    async def compute_metrics(
        self, 
        user_input: str, 
        intent: IntentResult, 
        memory_manager: MemoryManager,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Calculates:
        - internal_confidence (0-1)
        - engine_capability (true/false)
        - memory_match_score (0-1)
        - rule_data (promoted pattern match)
        """
        text = user_input.lower().strip()
        
        # 1. Internal Confidence
        internal_confidence = intent.confidence_score if intent else 0.5
        if intent and intent.intent_type == "greeting":
            internal_confidence = 1.0

        # 2. Engine Capability (Deterministic Check)
        engine_capability = False
        capable_engine = None
        
        # Math & Stats Detection
        is_math = any(re.search(p, text) for p in self.math_patterns)
        is_stats = any(re.search(rf"\b{re.escape(k)}\b", text) for k in self.stats_keywords)

        if is_math:
            engine_capability = True
            capable_engine = "deterministic"
        elif is_stats or "list" in text or "data" in text:
            engine_capability = True
            capable_engine = "data"

        # Code Detection
        elif intent and intent.intent_type == "code":
            engine_capability = True
            capable_engine = "code"
            
        # KG / Knowledge Graph Detection
        elif (intent and intent.intent_type == "knowledge") or any(k in text for k in ["relation", "neo4j", "connected to", "cypher"]):
            engine_capability = True
            capable_engine = "knowledge"

        # Doc/RAG Detection
        elif (intent and intent.intent_type == "document") or "rag" in text or "search documents" in text:
            engine_capability = True
            capable_engine = "document_agent"

        # Search/Research Detection
        elif (intent and intent.intent_type == "search") or any(k in text for k in ["search web", "tavily", "latest news"]):
            engine_capability = True
            capable_engine = "research_agent"

        # 3. Evolution Engine Lookup (Promoted Rules)
        rule_data = self.evolution_engine.apply(user_input)
        has_rule = rule_data is not None
        
        # 4. Fragility Assessment
        fragility = FragilityTracker.get_fragility(user_id, intent.intent_type if intent else "general")

        # 5. Memory Match Score (v8.15 Smart Ranking)
        memory_match_score = 0.0
        context = await memory_manager.get_combined_context(user_id, session_id, user_input)
        
        # Smart Ranking: (importance * 0.7) + (recency * 0.3) 
        # This is handled within MemoryManager in v8.15, but we check the resonance here.
        if context.get("graph_resonance", []):
            memory_match_score = 0.95
        elif context.get("long_term"):
            memory_match_score = 0.9
        elif context.get("short_term"):
            memory_match_score = 0.65
            
        return {
            "internal_confidence": internal_confidence,
            "engine_capability": engine_capability,
            "capable_engine": capable_engine,
            "has_rule": has_rule,
            "rule_data": rule_data,
            "fragility": fragility,
            "memory_match_score": memory_match_score,
            "is_abstract": self.is_abstract_query(text)
        }

    def decide(self, metrics: Dict[str, Any]) -> str:
        """
        LeviBrain Priority Algorithm v8.15:
        1. Abstract Override -> LLM
        2. Promoted Rule Rule -> RULE (Perfect Determinism)
        3. Engine Capable -> ENGINE (Deterministic Logic)
        4. High Memory Match -> MEMORY (Contextual shortcut)
        5. Internal Confidence -> INTERNAL
        6. Fallback -> LLM
        """
        if metrics.get("is_abstract"):
            return "LLM"
            
        if metrics.get("has_rule"):
            return "RULE"

        if metrics.get("fragility", 0) >= 0.8:
            return "LLM"

        # Reinforcement Loop (v12.0): Check if engine reward is sufficient
        if metrics["engine_capability"]:
            reward = self._get_agent_reward(metrics["capable_engine"])
            if reward < -0.5: # Significant negative reward threshold
                logger.warning(f"[Decision] Low reward ({reward}) for agent '{metrics['capable_engine']}'. Falling back to LLM.")
                return "LLM"
            return "ENGINE"
        
        if metrics["memory_match_score"] >= 0.75: # Higher threshold for direct memory shortcut
            return "MEMORY"

        if metrics["internal_confidence"] >= 0.7:
            return "INTERNAL"
            
        # v11.0: If high complexity but no clear winner -> Trigger Swarm Consensus
        if metrics.get("fragility", 0) > 0.5 or metrics.get("is_abstract"):
             return "EXPERT_REVIEW"

        return "LLM"
