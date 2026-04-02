import json
import logging
from typing import List, Dict, Any, Optional
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)

class BrainPlanner:
    """
    Cognitive Mission Planning v7.
    Deconstructs user intent into logical execution strategies.
    Aligns with the Sovereign Agent Registry.
    """
    
    def __init__(self):
        # Mission Templates for v7 Archetypes
        self._templates = {
            "RAG_SEARCH": [
                {"step": 1, "agent_name": "document", "params": {"collection_name": "sovereign_docs"}},
                {"step": 2, "agent_name": "search", "params": {"mode": "hybrid"}},
                {"step": 3, "agent_name": "memory", "depends_on": 1},
                {"step": 4, "agent_name": "critic", "depends_on": 2}
            ],
            "KNOWLEDGE_QUERY": [
                {"step": 1, "agent_name": "search", "params": {"mode": "hybrid"}},
                {"step": 2, "agent_name": "critic", "depends_on": 1}
            ],
            "CAUSAL_LOGIC": [
                {"step": 1, "agent_name": "python", "params": {"timeout": 10}},
                {"step": 2, "agent_name": "critic", "depends_on": 1}
            ],
            "VISUAL_STUDIO": [
                {"step": 1, "agent_name": "image", "params": {"style": "cinematic"}},
                {"step": 2, "agent_name": "chat", "params": {"mood": "creative"}}
            ],
            "DEEP_RESEARCH": [
                {"step": 1, "agent_name": "research", "params": {"depth": 2}},
                {"step": 2, "agent_name": "critic", "depends_on": 1}
            ]
        }

    async def classify_task(self, query: str) -> str:
        """
        Sophisticated intent classification for Sovereign OS v7.
        Ensures correct engine fleet assignment for complex user missions.
        """
        q_lower = query.lower()
        
        # 1. Visual/Cinematic Intent (Image/Video Generation)
        if any(w in q_lower for w in ["image", "picture", "generate", "draw", "painting", "render", "photo"]):
            return "VISUAL_STUDIO"
        if any(w in q_lower for w in ["video", "motion", "clip", "animation"]):
            return "VISUAL_STUDIO"
        
        # 2. RAG/Document/Paper Intent
        if any(w in q_lower for w in ["document", "pdf", "file", "read", "extract", "paper", "summarize"]):
            return "RAG_SEARCH"
            
        # 3. Logic/Math/Python/Reasoning Intent
        if any(w in q_lower for w in ["why", "logic", "calculate", "reason", "proof", "math", "code", "python", "debug"]):
            return "CAUSAL_LOGIC"
            
        # 4. Deep Research/Report/Survey Intent
        if any(w in q_lower for w in ["research", "deep dive", "report", "analysis", "survey", "history"]):
            return "DEEP_RESEARCH"
            
        # 5. Search/Knowledge/News Intent (Requires real-time web access)
        if any(w in q_lower for w in ["who is", "what is", "where is", "latest", "news", "price", "stock", "current"]):
            return "KNOWLEDGE_QUERY"
            
        # Default to high-fidelity Conversational Model
        return "CHAT"

    async def create_plan(self, query: str, intent: str) -> List[Dict[str, Any]]:
        """
        Generates the standard v7 mission plan.
        """
        logger.info(f"Planning Mission Strategy: {intent}")
        
        plan = self._templates.get(intent, [{"step": 1, "agent_name": "chat"}])
        
        # Inject user query into the first step if applicable
        final_plan = []
        for step in plan:
            new_step = step.copy()
            new_params = new_step.get("params", {}).copy()
            
            # Universal mission input
            if "input" not in new_params:
                new_params["input"] = query
            
            new_step["params"] = new_params
            final_plan.append(new_step)
            
        return final_plan
