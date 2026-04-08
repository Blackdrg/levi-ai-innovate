"""
Sovereign Tool Registry v8.
Unified registry for the autonomous Agent Ecosystem.
Refactored to point to the tiered backend structure.
"""

import logging
from typing import Dict, Any, Optional
from backend.utils.network import standard_retry, ai_service_breaker
from backend.core.execution_guardrails import AgentSandbox

# Importing from the new tiered agent ecosystem (V8 Hardened)
from backend.core.v8.agents.chat import ChatAgentV8
from backend.core.v8.agents.code import CodeAgentV8
from backend.core.v8.agents.document import DocumentAgentV8
from backend.core.v8.agents.research import ResearchAgentV8
from backend.core.v8.agents.python_repl import PythonReplAgentV8
from backend.core.v8.agents.consensus import ConsensusAgentV8
from backend.core.v8.agents.relation_agent import RelationAgentV8
from backend.core.v8.agents.critic import CriticAgentV8
from backend.core.v8.agents.mental_compressor import MentalCompressorAgent

# Legacy / Non-reasoning agents
from backend.agents.image_agent import ImageAgent
from backend.agents.local_agent import LocalAgent
from backend.agents.video_agent import VideoAgent
from backend.agents.diagnostic_agent import DiagnosticAgent
from backend.agents.optimizer_agent import OptimizerAgent
from backend.agents.task_agent import TaskAgent
from backend.agents.memory_agent import MemoryAgent

logger = logging.getLogger(__name__)

from backend.engines.deterministic_engine import DeterministicEngine

# Registry of tool instances (V8 Synchronized)
_TOOL_INSTANCES: Dict[str, Any] = {
    "chat_agent":   ChatAgentV8(),
    "image_agent":  ImageAgent(),
    "code_agent":   CodeAgentV8(),
    "search_agent": ResearchAgentV8(), # V8 Research agent handles search missions
    "local_agent":  LocalAgent(),
    "python_repl_agent": PythonReplAgentV8(),
    "video_agent": VideoAgent(),
    "critic_agent": CriticAgentV8(),
    "diagnostic_agent": DiagnosticAgent(),
    "optimizer_agent": OptimizerAgent(),
    "document_agent": DocumentAgentV8(),
    "research_agent": ResearchAgentV8(),
    "task_agent": TaskAgent(),
    "memory_agent": MemoryAgent(),
    "consensus_agent": ConsensusAgentV8(),
    "relation_agent": RelationAgentV8(),
    "mental_compressor": MentalCompressorAgent(),
    "deterministic_engine": DeterministicEngine(),
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
    if not AgentSandbox.tool_allowed(name):
        logger.warning("Tool boundary violation blocked for '%s'", name)
        return {
            "success": False,
            "error": f"Tool boundary violation: '{name}' is not permitted for this task.",
            "agent": name,
        }
    
    try:
        sandbox_ctx = AgentSandbox.current()
        call_context = dict(context or {})
        if sandbox_ctx.get("memory_scope_key"):
            call_context["session_id"] = sandbox_ctx["memory_scope_key"]
            params = {
                **params,
                "__memory_scope_key__": sandbox_ctx["memory_scope_key"],
                "__allowed_tools__": sorted(sandbox_ctx.get("allowed_tools", set())),
            }

        # Standard resilient call pattern for V8
        async def _core_call():
             # Most agents use the standardized 'execute' method from base.py
             if hasattr(agent, "execute"):
                 return await agent.execute(params, **call_context)
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
