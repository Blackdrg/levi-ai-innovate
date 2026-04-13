import abc
import logging
import time
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from backend.engines.utils.security import SovereignSecurity
from backend.engines.utils.i18n import SovereignI18n

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
    citations: List[str] = Field(default_factory=list)

class SovereignAgent(abc.ABC, Generic[T, R]):
    """
    Abstract Base Class for all LEVI-AI Sovereign Agents.
    Provides standardized mission lifecycle, security masking, and multi-step recovery.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name.lower()}")

    async def execute(self, input_data: T, lang: str = "en", **kwargs) -> AgentResult:
        """
        Main execution wrapper for Agentic Missions.
        """
        start_time = time.perf_counter()
        self.logger.info(f"Agent {self.name} received mission.")
        
        # 1. Security Input Scrubbing
        input_dict = input_data.dict() if hasattr(input_data, "dict") else str(input_data)
        # Deep PII masking on input could be added here if needed
        
        try:
            # 2. Iterative Mission Execution (Reflexive Correction Loop)
            max_retries = kwargs.get("agent_max_retries", 2)
            for attempt in range(max_retries + 1):
                try:
                    result_data = await self._run(input_data, lang=lang, **kwargs)
                    break
                except Exception as eval_err:
                    if attempt >= max_retries:
                        raise eval_err
                    self.logger.warning(f"Agent {self.name} reflexive retry {attempt+1}/{max_retries} due to: {eval_err}")
                    # Fast-path correction prompt context could be injected via kwargs here
                    kwargs["last_error"] = str(eval_err)
                    
            latency = (time.perf_counter() - start_time) * 1000
            
            # 3. Output Sanitization
            if isinstance(result_data, dict):
                msg = result_data.get("message", "")
                data = result_data.get("data", {})
                citations = result_data.get("citations", [])
            else:
                msg = str(result_data)
                data = {}
                citations = []

            # Mask PII in final output
            safe_msg = SovereignSecurity.mask_pii(msg)
            
            return AgentResult(
                success=True,
                message=safe_msg,
                data=data,
                agent=self.name,
                latency_ms=latency,
                citations=citations
            )
            
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

    async def request_side_mission(self, user_id: str, session_id: str, objective: str, **kwargs) -> AgentResult:
        """
        Sovereign v15.0: Autonomous Side-Mission Request.
        Allows an agent to spawn a sub-mission to solve complex dependencies.
        """
        self.logger.info(f"🚀 [Autonomy] Agent {self.name} requesting side-mission: {objective[:50]}...")
        from backend.core.orchestrator import Orchestrator
        # We use a late import and local instance to avoid circular dependency
        # In a fully optimized system, this would use a registry or shared bus
        orchestrator = Orchestrator()
        
        result = await orchestrator.handle_mission(
            user_input=objective,
            user_id=user_id,
            session_id=session_id,
            is_side_mission=True,
            **kwargs
        )
        
        # Convert orchestrator output to AgentResult
        if isinstance(result, dict):
             return AgentResult(
                 success=result.get("status") == "success",
                 message=result.get("response", ""),
                 data=result,
                 agent="orchestrator_sub_mission"
             )
        return AgentResult(success=False, message="Side-mission failed.")

    @abc.abstractmethod
    async def _run(self, input_data: T, lang: str = "en", **kwargs) -> Any:
        """Internal mission implementation to be overridden by subclasses."""
        pass
