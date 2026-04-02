import abc
import logging
import time
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)

class AgentResult(BaseModel):
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    agent: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0
    citations: List[str] = Field(default_factory=list)

class BaseV8Agent(abc.ABC, Generic[T]):
    """
    LeviBrain v8: Base Agent Contract
    Agents are now 'Systems' with internal scoring, parallel tasks, and self-correction.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"v8.agent.{name.lower()}")

    async def run(self, input_data: T, context: Dict[str, Any] = None) -> AgentResult:
        """Standardized entry point for all V8 system agents."""
        start_time = time.perf_counter()
        self.logger.info(f"V8 Agent {self.name} starting mission.")
        
        try:
            # 1. Perception/Input handling is handled by the Brain
            # 2. Execute internal system logic
            result = await self._execute_system(input_data, context or {})
            
            latency = (time.perf_counter() - start_time) * 1000
            result.agent = self.name
            result.latency_ms = latency
            return result
            
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"V8 Agent {self.name} system failure: {e}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
                message=f"The {self.name} system encountered a logic breach.",
                agent=self.name,
                latency_ms=latency
            )

    @abc.abstractmethod
    async def _execute_system(self, input_data: T, context: Dict[str, Any]) -> AgentResult:
        """Internal system implementation to be overridden."""
        pass
