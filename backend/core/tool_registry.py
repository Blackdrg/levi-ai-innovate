"""
Sovereign Tool Registry v8.
Unified registry for the autonomous Agent Ecosystem.
Refactored to point to the tiered backend structure.
"""

import logging
from typing import Dict, Any, Type, Optional
from backend.utils.network import standard_retry, ai_service_breaker

# Importing from the new tiered agent ecosystem
from backend.agents.chat_agent import ChatAgent
from backend.agents.image_agent import ImageAgent
from backend.agents.code_agent import CodeAgent
from backend.agents.search_agent import SearchAgent
from backend.agents.local_agent import LocalAgent
from backend.agents.python_repl_agent import PythonREPLAgent
from backend.agents.video_agent import VideoAgent
from backend.agents.critic_agent import CriticAgent
from backend.agents.diagnostic_agent import DiagnosticAgent
from backend.agents.optimizer_agent import OptimizerAgent
from backend.agents.document_agent import DocumentAgent
from backend.agents.research_agent import ResearchAgent
from backend.agents.task_agent import TaskAgent
from backend.agents.memory_agent import MemoryAgent
from backend.core.v8.agents.consensus import ConsensusAgentV8
from backend.core.v8.agents.relation_agent import RelationAgentV8

logger = logging.getLogger(__name__)

# Registry of tool instances (retaining the name mapping for the V8 Orchestrator)
_TOOL_INSTANCES: Dict[str, Any] = {
    "chat_agent":   ChatAgent(),
    "image_agent":  ImageAgent(),
    "code_agent":   CodeAgent(),
    "search_agent": SearchAgent(),
    "local_agent":  LocalAgent(),
    "python_repl_agent": PythonREPLAgent(),
    "video_agent": VideoAgent(),
    "critic_agent": CriticAgent(),
    "diagnostic_agent": DiagnosticAgent(),
    "optimizer_agent": OptimizerAgent(),
    "document_agent": DocumentAgent(),
    "research_agent": ResearchAgent(),
    "task_agent": TaskAgent(),
    "memory_agent": MemoryAgent(),
    "consensus_agent": ConsensusAgentV8(),
    "relation_agent": RelationAgentV8(),
}

def get_tool(name: str) -> Optional[Any]:
    """Retrieve an agent instance by name."""
    return _TOOL_INSTANCES.get(name)

async def call_tool(name: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
    """
    Entry point for calling an agent by name.
    Provides standardized resilient execution via Retries and Circuit Breakers.
    """
    agent = get_tool(name)
    if not agent:
        logger.error(f"Agent '{name}' not found in ecosystem.")
        return {
            "success": False,
            "error": f"The '{name}' neural link is currently severed.",
            "agent": name
        }
    
    try:
        # Standard resilient call pattern for V8
        async def _core_call():
             # Most agents use the standardized 'execute' method from base.py
             if hasattr(agent, "execute"):
                 return await agent.execute(params, **(context or {}))
             # Fallback for non-standard tools if any
             return await agent(params)

        return await ai_service_breaker.async_call(
            standard_retry.wraps(_core_call)
        )
    except Exception as e:
        logger.exception(f"Resilient agent call failure for '{name}': {e}")
        return {
            "success": False,
            "error": f"The mission was aborted by a neural anomaly: {str(e)}",
            "agent": name
        }

def list_tools() -> Dict[str, str]:
    """Returns a map of agent names and their descriptions (if available)."""
    return {name: getattr(agent, "description", "Autonomous Agent") for name, agent in _TOOL_INSTANCES.items()}
