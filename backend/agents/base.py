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

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)

class SovereignAgent(abc.ABC, Generic[T, R]):
    """
    Abstract Base Class for all LEVI-AI Sovereign Agents.
    Architecture: Identity -> Input Scrubbing -> Execution -> Output Sanitization.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name.lower()}")

    async def execute(self, input_data: T, lang: str = "en", **kwargs) -> AgentResult:
        """
        Main execution wrapper for Agentic Missions.
        Handles PII masking and standardized reporting.
        """
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

    @abc.abstractmethod
    async def _run(self, input_data: T, lang: str = "en", **kwargs) -> Any:
        """Internal mission implementation."""
        pass
