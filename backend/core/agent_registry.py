import logging
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel

from backend.core.agent_base import SovereignAgent, AgentResult
from backend.core.v8.agents.chat import ChatAgentV8 as ChatAgent
from backend.core.v8.agents.code import CodeAgentV8 as CodeAgent
from backend.core.v8.agents.document import DocumentAgentV8 as DocumentAgent
from backend.core.v8.agents.research import ResearchAgentV8 as ResearchAgent
from backend.core.v8.agents.python_repl import PythonReplAgentV8 as PythonReplAgent
from backend.core.v8.agents.critic import CriticAgentV8 as CriticAgent

# Specialized/Legacy Support
from backend.agents.image_agent import ImageAgent
from backend.agents.video_agent import VideoAgent
from backend.agents.local_agent import LocalAgent
from backend.agents.memory_agent import MemoryAgent
from backend.agents.optimizer_agent import OptimizerAgent
from backend.agents.task_agent import TaskAgent
from backend.agents.diagnostic_agent import DiagnosticAgent


logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    Central Registry for the Sovereign Agent Fleet v7.
    Handles mission routing, instance management, and schema validation.
    """
    
    _agents: Dict[str, Type[SovereignAgent]] = {
        "chat": ChatAgent,
        "code": CodeAgent,
        "critic": CriticAgent,
        "diagnostic": DiagnosticAgent,
        "document": DocumentAgent,
        "image": ImageAgent,
        "video": VideoAgent,
        "local": LocalAgent,
        "memory": MemoryAgent,
        "optimizer": OptimizerAgent,
        "python": PythonReplAgent,
        "research": ResearchAgent,
        "task": TaskAgent
    }

    @classmethod
    async def dispatch(cls, name: str, context: Dict[str, Any], lang: str = "en") -> AgentResult:
        """
        Dispatches a mission to the specified Sovereign Agent.
        Verifies schema and executes within the standardized agent lifecycle.
        """
        agent_cls = cls._agents.get(name.lower())
        input_cls = cls._inputs.get(name.lower())

        if not agent_cls or not input_cls:
            logger.error(f"Agent Registry: Agent '{name}' is not commissioned.")
            return AgentResult(
                success=False, 
                error=f"Agent '{name}' not found.",
                agent="Registry"
            )

        try:
            # 1. Instantiate Agent (Per-mission for isolation)
            agent = agent_cls()
            
            # 2. Mission Schema Preparation
            # v8 Agents expect a Dict or Pydantic model directly.
            mission_input = {
                "input": context.get("query", context.get("message", context.get("text", ""))),
                **context
            }

            # 3. Execute Mission
            logger.info(f"Registry: Dispatching '{name}' mission (v8).")
            if hasattr(agent, "execute"):
                 return await agent.execute(mission_input, lang=lang)
            return await agent(mission_input)

        except Exception as e:
            logger.exception(f"Registry: Mission Dispatch Failure for '{name}': {e}")
            return AgentResult(
                success=False,
                error=str(e),
                agent=name
            )

    @classmethod
    def get_commissioned_agents(cls) -> list:
        return list(cls._agents.keys())
