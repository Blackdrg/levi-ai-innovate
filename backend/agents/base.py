"""
Sovereign Agent Base v8.
Provides the foundation for autonomous agents with standardized execution,
security masking, and multi-step recovery.
"""

import abc
import logging
import asyncio
import time
from typing import Any, Dict, List, Optional, Generic, TypeVar, Type
from pydantic import BaseModel, Field

# Local imports from utility layer
from backend.engines.utils.security import SovereignSecurity
from backend.engines.utils.i18n import SovereignI18n
from backend.services.agent_bus import sovereign_bus, AgentBus
from backend.redis_client import cache

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)

logger = logging.getLogger(__name__)

class AgentResult(BaseModel):
    """Standardized output for all Sovereign Agents."""
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    agent: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    citations: List[str] = Field(default_factory=list)
    fidelity_score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)

class AgentState(BaseModel):
    """Internal state for a Sovereign Agent."""
    memory: List[Dict[str, Any]] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    strategy: str = Field("optimize", pattern="^(optimize|explore|verify)$")

class SovereignAgent(abc.ABC, Generic[T, R]):
    """
    Abstract Base Class for all LEVI-AI Sovereign Agents.
    Architecture: Identity -> Input Scrubbing -> Execution -> Output Sanitization.
    """
    
    def __init__(self, name: str, profile: str = "Standard", use_bus: bool = False):
        self.name = name
        self.profile = profile # Neural Profile (e.g. The Architect)
        self.system_prompt_template = "" # Domain-specific instructions
        self.logger = logging.getLogger(f"agent.{name.lower()}")
        if use_bus:
            self.bus = sovereign_bus
            self.bus.register(self.name.lower())
        else:
            self.bus = None
        
        # Phase 2: State Persistence
        self.state = AgentState()

    def _get_state_key(self, session_id: str) -> str:
        return f"sovereign:agent:state:{self.name.lower()}:{session_id}"

    async def save_state(self, session_id: str):
        """Persists the current agent state to Redis."""
        key = self._get_state_key(session_id)
        try:
            # Use json.dumps because cache.set expects a string value
            import json
            cache.set(key, self.state.model_dump_json(), ex=86400) # 24h
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    async def load_state(self, session_id: str):
        """Loads agent state from Redis."""
        key = self._get_state_key(session_id)
        data = cache.get(key)
        if data:
            try:
                self.state = AgentState.model_validate_json(data)
            except Exception as e:
                self.logger.error(f"Failed to parse loaded state: {e}")

    async def send(self, to_agent: str, data: Dict[str, Any]):
        """Alias for send_message to comply with Phase 2 specs."""
        await self.send_message(to_agent, data)

    async def send_message(self, to_agent: str, message: Dict[str, Any]):
        """Directly send a message via the Agent Bus."""
        if self.bus:
            await self.bus.send(to_agent.lower(), message)

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """Wait for a message from the Agent Bus."""
        if self.bus:
            return await self.bus.receive(self.name.lower())
        return None

    async def execute(self, input_data: T, lang: str = "en", **kwargs) -> AgentResult:
        """
        Main execution wrapper for Agentic Missions.
        Handles PII masking and standardized reporting.
        """
        session_id = getattr(input_data, "session_id", kwargs.get("session_id"))
        if session_id:
            await self.load_state(session_id)

        start_time = time.perf_counter()
        self.logger.info(f"Agent {self.name} received mission.")
        
        try:
            # 1. Mission Execution
            result_data = await self._run(input_data, lang=lang, **kwargs)
            
            latency = (time.perf_counter() - start_time) * 1000
            
            # 2. Result Normalization
            if isinstance(result_data, dict):
                msg = result_data.get("message", "")
                data = result_data.get("data", {})
                citations = result_data.get("citations", [])
            elif isinstance(result_data, AgentResult):
                return result_data
            else:
                msg = str(result_data)
                data = {}
                citations = []

            # 3. Sovereign Shield: Output Sanitization
            safe_msg = SovereignSecurity.mask_pii(msg)
            
            agent_res = AgentResult(
                success=True,
                message=safe_msg,
                data=data,
                agent=self.name,
                latency_ms=latency,
                citations=citations,
                fidelity_score=result_data.get("score", 0.0) if isinstance(result_data, dict) else 0.0,
                metadata=result_data.get("metadata", {}) if isinstance(result_data, dict) else {}
            )
            
            # Post-execution persistence
            if session_id:
                await self.save_state(session_id)
            
            return agent_res
            
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Agent {self.name} mission failure: {str(e)}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
                message=SovereignI18n.get_prompt("error_fallback", lang),
                agent=self.name,
                latency_ms=latency
            )

    @abc.abstractmethod
    async def _run(self, input_data: T, lang: str = "en", **kwargs) -> Any:
        """Internal mission implementation."""
        pass
