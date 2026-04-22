import logging
from typing import List, Dict, Any

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
                {"step": 1, "agent_name": "memory"},
                {"step": 2, "agent_name": "researcher", "depends_on": [1]},
                {"step": 3, "agent_name": "critic", "depends_on": [2]}
            ],
            "KNOWLEDGE_QUERY": [
                {"step": 1, "agent_name": "researcher"},
                {"step": 2, "agent_name": "critic", "depends_on": [1]}
            ],
            "CAUSAL_LOGIC": [
                {"step": 1, "agent_name": "researcher"},
                {"step": 2, "agent_name": "critic", "depends_on": [1]},
                {"step": 3, "agent_name": "writer", "depends_on": [2]}
            ],
            "DEEP_RESEARCH": [
                {"step": 1, "agent_name": "researcher"},
                {"step": 2, "agent_name": "critic", "depends_on": [1]},
                {"step": 3, "agent_name": "writer", "depends_on": [2]}
            ],
            "DATA_SYNTHESIS": [
                {"step": 1, "agent_name": "memory"},
                {"step": 2, "agent_name": "researcher", "depends_on": [1]},
                {"step": 3, "agent_name": "writer", "depends_on": [2]}
            ],
            "VISUAL_STUDIO": [
                {"step": 1, "agent_name": "researcher"},
                {"step": 2, "agent_name": "writer", "depends_on": [1]}
            ]
        }

    async def classify_task(self, query: str) -> str:
        """
        Sophisticated intent classification for Sovereign OS v7.
        """
        q_lower = query.lower()
        
        if any(w in q_lower for w in ["image", "picture", "draw", "painting"]):
            return "VISUAL_STUDIO"
        if any(w in q_lower for w in ["document", "pdf", "file", "summarize"]):
            return "RAG_SEARCH"
        if any(w in q_lower for w in ["why", "logic", "reason", "math", "code", "python"]):
            return "CAUSAL_LOGIC"
        if any(w in q_lower for w in ["research", "report", "analysis", "survey"]):
            return "DEEP_RESEARCH"
        if any(w in q_lower for w in ["who is", "latest", "news", "current"]):
            return "KNOWLEDGE_QUERY"
            
        return "CHAT"

    async def create_plan(self, query: str, intent: str) -> List[Dict[str, Any]]:
        \"\"\"
        Generates the mission plan. Uses dynamic architecting for complex intents.
        \"\"\"
        logger.info(f"Planning Mission Strategy: {intent}")
        
        # 🎓 Tier 3: Strategy Cache (DAG Reuse)
        from backend.redis_client import get_cached_json, cache_json
        cache_key = f"t3_strat:{intent}:{query}"
        cached = get_cached_json(cache_key)
        if cached:
            logger.info(f"🎯 [Brain-Planner] T3 STRATEGY HIT for {intent}")
            return cached

        if intent in ["CAUSAL_LOGIC", "DEEP_RESEARCH"]:
            plan = await self.create_dynamic_plan(query, intent)
            if plan:
                cache_json(cache_key, plan, expire=86400) # Cache for 24h
            return plan
            
        plan = self._templates.get(intent, [{"step": 1, "agent_name": "chat"}])
        return self._inject_query(plan, query)

    async def create_dynamic_plan(self, query: str, intent: str) -> List[Dict[str, Any]]:
        """
        Sovereign v22.1: Dynamic DAG generation via Cognition Architect.
        """
        logger.info(f"🚀 [Planner] Dynamically architecting mission for: {intent}")
        from .orchestrator import distributed_orchestrator
        
        prompt = (
            f"Architect a mission for: {query}\n"
            f"Intent: {intent}\n"
            "Return a JSON list of steps. Each step: {'step': int, 'agent_name': str, 'depends_on': list of ints or null, 'params': dict}\n"
            "Available Agents: RESEARCHER, CRITIC, WRITER, MEMORY, CHAT.\n\n"
            "### SCHEDULING HEURISTIC (Section 83.1)\n"
            "Apply the Critical-Path Heuristic: Priority = Complexity + Σ Latency(Children).\n"
            "Group independent steps into early waves to minimize total mission latency."
        )
        
        res = await distributed_orchestrator.execute_task("planner", "COGNITION", prompt)
        
        if res.get("status") == "completed":
            try:
                import json
                import re
                match = re.search(r"\[.*\]", res.get("output", ""), re.DOTALL)
                if match:
                    plan = json.loads(match.group())
                    return self._inject_query(plan, query)
            except Exception as e:
                logger.error(f"Failed to parse dynamic plan: {e}")
        
        return self._inject_query(self._templates.get(intent, [{"step": 1, "agent_name": "chat"}]), query)

    def _inject_query(self, plan: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        final_plan = []
        for step in plan:
            new_step = step.copy()
            new_params = new_step.get("params", {}).copy()
            if "input" not in new_params:
                new_params["input"] = query
            new_step["params"] = new_params
            final_plan.append(new_step)
        return final_plan
