"""
Sovereign Mission Blackboard v13.1.0.
A high-fidelity, transient context layer for inter-agent cognitive synchronization.
Uses zlib compression for efficient shared-state exchange.
"""

import zlib
import json
import base64
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class BlackboardState(BaseModel):
    """
    Structured schema for the Mission Blackboard.
    """
    mission_id: str
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    agent_insights: Dict[str, str] = Field(default_factory=dict)
    tool_artifacts: Dict[str, Any] = Field(default_factory=dict)
    fidelity_markers: Dict[str, float] = Field(default_factory=dict)

class MissionBlackboard:
    """
    The 'Mission Blackboard' is a transient, per-session context layer.
    Agents can read/write insights without database round-trips.
    """
    
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.state = BlackboardState(mission_id=mission_id)
        self._lock = None # Could use asyncio.Lock() if needed

    def update_insight(self, agent_name: str, insight: str):
        """Adds a strategic insight from an agent."""
        self.state.agent_insights[agent_name] = insight
        logger.info(f"[Blackboard] Insight recorded from {agent_name} for mission {self.mission_id}")

    def add_artifact(self, key: str, data: Any):
        """Stores a tool-produced artifact for other agents to consume."""
        self.state.tool_artifacts[key] = data

    def get_context_summary(self) -> str:
        """Returns a string representation of the blackboard for agent consumption."""
        summary = f"Mission Blackboard ({self.mission_id}):\n"
        if self.state.agent_insights:
            summary += "Current Insights:\n" + "\n".join([f"- {a}: {i}" for a, i in self.state.agent_insights.items()])
        if self.state.tool_artifacts:
            summary += "\nAvailable Artifacts: " + ", ".join(self.state.tool_artifacts.keys())
        return summary

    def serialize(self) -> str:
        """Serializes and compresses the blackboard for transport (e.g. SSE or Gossip)."""
        raw_json = self.state.json()
        compressed = zlib.compress(raw_json.encode('utf-8'))
        return base64.b64encode(compressed).decode('utf-8')

    @classmethod
    def deserialize(cls, mission_id: str, blob: str) -> 'MissionBlackboard':
        """Reconstructs a blackboard from a compressed blob."""
        compressed = base64.b64decode(blob)
        raw_json = zlib.decompress(compressed).decode('utf-8')
        data = json.loads(raw_json)
        bb = cls(mission_id)
        bb.state = BlackboardState(**data)
        return bb
