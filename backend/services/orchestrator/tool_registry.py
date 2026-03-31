"""
backend/services/orchestrator/tool_registry.py

Unified registry for the hardened LEVI-AI tool system.
"""

import logging
from typing import Dict, Any, Type, Optional
from .tool_base import BaseTool
from .agents.chat_agent import ChatAgent
from .agents.image_agent import ImageAgent
from .agents.code_agent import CodeAgent
from .agents.search_agent import SearchAgent
from .agents.local_agent import LocalAgent
from .agents.python_repl_agent import PythonREPLAgent
from .agents.video_agent import VideoAgent
from .agents.critic_agent import ValidatorAgent
from .agents.diagnostic_agent import DiagnosticAgent
from .agents.optimizer_agent import OptimizerAgent

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
    "critic_agent": ValidatorAgent(),
    "diagnostic_agent": DiagnosticAgent(),
    "optimizer_agent": OptimizerAgent(),
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
        # This will trigger BaseTool.execute()
        return await tool.execute(params, context)
    except Exception as e:
        logger.exception(f"Fatal error in call_tool for '{name}': {e}")
        return {
            "success": False,
            "error": str(e),
            "agent": name
        }

def list_tools() -> Dict[str, str]:
    """Returns a map of tool names and their descriptions."""
    return {name: tool.description for name, tool in _TOOL_INSTANCES.items()}
