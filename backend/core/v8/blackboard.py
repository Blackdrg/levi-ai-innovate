"""
Sovereign Mission Blackboard v8.
A shared, session-scoped memory buffer for agent collaboration.
Enables 'Swarm Intelligence' by allowing agents to post insights and pull context.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from backend.redis_client import SovereignCache

logger = logging.getLogger(__name__)

class MissionBlackboard:
    """
    Session-scoped key-value store for agent coordination.
    Uses Redis for high-speed R/W.
    """
    
    BASE_KEY = "sovereign:blackboard"

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client = SovereignCache.get_client()
        self.key = f"{self.BASE_KEY}:{session_id}"

    async def post_insight(self, agent_id: str, data: Any, tag: str = "general"):
        """Posts an insight from an agent to the blackboard."""
        insight = {
            "agent": agent_id,
            "data": data,
            "tag": tag,
            "timestamp": None # In real production, use actual timestamp
        }
        
        # 🛡️ Resilience: Graceful fallback for air-gapped or local-only mode
        try:
            self.client.rpush(self.key, json.dumps(insight))
            logger.debug(f"[Blackboard] Insight posted by {agent_id} (Session {self.session_id})")
        except Exception as e:
            logger.warning(f"⚠️ [Blackboard] Redis unreachable. Insight from {agent_id} suppressed: {e}")

    async def get_insights(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all insights for the current session."""
        try:
            raw_list = self.client.lrange(self.key, 0, -1)
            insights = [json.loads(r) for r in raw_list]
        except Exception:
            logger.debug(f"[Blackboard] Switched to offline mode for session {self.session_id}")
            return []
        
        if tag:
            return [i for i in insights if i.get("tag") == tag]
        return insights

    async def clear(self):
        """Clears the blackboard for this session."""
        try:
            self.client.delete(self.key)
            logger.info(f"[Blackboard] Session {self.session_id} cleared.")
        except: pass

    @classmethod
    async def get_session_context(cls, session_id: str) -> str:
        """Helper to get a text summary of the blackboard for LLM input."""
        blackboard = cls(session_id)
        insights = await blackboard.get_insights()
        
        if not insights:
            return "No prior insights in mission blackboard."
            
        summary = "--- Mission Blackboard Context ---\n"
        for i in insights:
            summary += f"[{i['agent']}]: {i['data']}\n"
        return summary
