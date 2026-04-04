import abc
import logging
import time
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from backend.core.orchestrator_types import AgentResult, AgentBase, ToolResult

T = TypeVar("T", bound=BaseModel)

class BaseV8Agent(AgentBase, abc.ABC, Generic[T]):
    """
    LeviBrain v9.8: Base Agent Contract
    Agents are now 'Systems' with internal scoring, parallel tasks, and self-correction.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"v8.agent.{name.lower()}")

    async def run(self, input_data: T, context: Dict[str, Any] = None) -> AgentResult[Any]:
        """Standardized entry point for all V8 system agents."""
        start_time = time.perf_counter()
        self.logger.info(f"V8 Agent {self.name} starting mission.")
        
        try:
            # 1. Execute internal system logic
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

    async def delegate_to(self, agent_name: str, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """
        Sovereign v9.8: Autonomous Swarm Delegation.
        Allows an agent to call another agent or engine directly.
        """
        from ..tool_registry import call_tool
        self.logger.info(f"Agent {self.name} delegating to {agent_name}...")
        
        try:
            # Standardized tool invocation (handles engines and agents)
            result = await call_tool(agent_name, input_data, context or {})
            
            # Convert to ToolResult if it's an AgentResult or dict
            if isinstance(result, AgentResult):
                return ToolResult(
                    success=result.success,
                    message=result.message,
                    data=result.data if isinstance(result.data, dict) else {"result": result.data},
                    agent=result.agent,
                    latency_ms=int(result.latency_ms)
                )
            elif isinstance(result, dict):
                return ToolResult(**result)
            return result
        except Exception as e:
            self.logger.error(f"Delegation failure from {self.name} to {agent_name}: {e}")
            return ToolResult(success=False, error=str(e), agent=agent_name)

    async def negotiate(self, target_agent: str, constraints: Dict[str, Any]) -> bool:
        """
        Sovereign v9.8.1: Swarm Negotiation.
        Ensures target agent supports required constraints (e.g. GPU, context_window).
        """
        from backend.core.agent_registry import AgentRegistry
        
        # Discover required capabilities from constraints
        required_caps = constraints.get("requires", [])
        if not required_caps:
            return True # No specific resonance required
            
        self.logger.info(f"[Negotiation] Verifying {target_agent} resonance for {required_caps}...")
        
        # For v9 Monolith: Capable agents are pre-defined in the Registry with metadata
        # In a real cluster, this would query the capability bus.
        agent_cls = AgentRegistry._agents.get(target_agent.lower())
        if not agent_cls:
            self.logger.error(f"[Negotiation] Target {target_agent} is not commissioned.")
            return False
            
        # Simplified metadata check: Agents can define a __capabilities__ attribute
        available_caps = getattr(agent_cls, "__capabilities__", ["general"])
        
        for cap in required_caps:
            if cap not in available_caps:
                self.logger.warning(f"[Negotiation] Agent {target_agent} lacks required capability: {cap}")
                return False
                
        self.logger.info(f"[Negotiation] Resonance achieved with {target_agent}.")
        return True

    @abc.abstractmethod
    async def _execute_system(self, input_data: T, context: Dict[str, Any]) -> AgentResult[Any]:
        """Internal system implementation to be overridden."""
        pass
