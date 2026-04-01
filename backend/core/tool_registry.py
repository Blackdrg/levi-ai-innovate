"""
backend/core/tool_registry.py

Unified registry for the hardened LEVI-AI v7 tool system.
"""

import logging
from typing import Dict, Any, Type, Optional
from .tool_base import BaseTool
from backend.utils.network import standard_retry, ai_service_breaker
from .agents.chat_agent import ChatAgent
from .agents.image_agent import ImageAgent
from .agents.code_agent import CodeAgent
from .agents.search_agent import SearchAgent
from .agents.local_agent import LocalAgent
from .agents.python_repl_agent import PythonREPLAgent
from .agents.video_agent import VideoAgent
from .agents.critic_agent import CriticAgent
from .agents.diagnostic_agent import DiagnosticAgent
from .agents.optimizer_agent import OptimizerAgent
from .agents.document_agent import DocumentAgent
from .agents.research_agent import ResearchAgent
from .agents.task_agent import TaskAgent
from .agents.memory_agent import MemoryAgent

logger = logging.getLogger(__name__)

# Registry of tool instances
_TOOL_INSTANCES: Dict[str, BaseTool] = {
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
}

def get_tool(name: str) -> Optional[BaseTool]:
    """Retrieve a tool instance by name."""
    return _TOOL_INSTANCES.get(name)

async def call_tool(name: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
    """
    Entry point for calling a tool by name.
    Ensures execution logic (validation/retry/timeout) from BaseTool is triggered.
    """
    tool = get_tool(name)
    if not tool:
        logger.error(f"Tool '{name}' not found in registry.")
        return {
            "success": False,
            "error": f"Tool '{name}' not found.",
            "agent": name
        }
    
    
    try:
        # Phase 6 Hardening: Apply Circuit Breaker and Retries
        async def _core_call():
             return await tool.execute(params, context)

        # We wrap the core call in a standard retry and then the circuit breaker
        return await ai_service_breaker.async_call(
            standard_retry.wraps(_core_call)
        )
    except Exception as e:
        logger.exception(f"Resilient call_tool failure for '{name}': {e}")
        return {
            "success": False,
            "error": f"The {name} encountered a cosmic barrier: {str(e)}",
            "agent": name
        }

def list_tools() -> Dict[str, str]:
    """Returns a map of tool names and their descriptions."""
    return {name: tool.description for name, tool in _TOOL_INSTANCES.items()}
