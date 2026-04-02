import logging
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel

from backend.core.agent_base import SovereignAgent, AgentResult
from backend.core.agents.chat_agent import ChatAgent, ChatInput
from backend.core.agents.code_agent import CodeAgent, CodeInput
from backend.core.agents.critic_agent import CriticAgent, CriticInput
from backend.core.agents.diagnostic_agent import DiagnosticAgent, DiagnosticInput
from backend.core.agents.document_agent import DocumentAgent, DocumentInput
from backend.core.agents.image_agent import ImageAgent, ImageInput
from backend.core.agents.video_agent import VideoAgent, VideoInput
from backend.core.agents.local_agent import LocalAgent, LocalInput
from backend.core.agents.memory_agent import MemoryAgent, MemoryInput
from backend.core.agents.optimizer_agent import OptimizerAgent, OptimizerInput
from backend.core.agents.python_repl_agent import PythonReplAgent, PythonInput
from backend.core.agents.research_agent import ResearchAgent, ResearchInput
from backend.core.agents.search_agent import SearchAgent, SearchInput
from backend.core.agents.task_agent import TaskAgent, TaskInput

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
        "search": SearchAgent,
        "task": TaskAgent
    }

    _inputs: Dict[str, Type[BaseModel]] = {
        "chat": ChatInput,
        "code": CodeInput,
        "critic": CriticInput,
        "diagnostic": DiagnosticInput,
        "document": DocumentInput,
        "image": ImageInput,
        "video": VideoInput,
        "local": LocalInput,
        "memory": MemoryInput,
        "optimizer": OptimizerInput,
        "python": PythonInput,
        "research": ResearchInput,
        "search": SearchInput,
        "task": TaskInput
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
            
            # 2. Validate & Cast Input Schema
            # We filter context to match input_cls fields
            valid_keys = input_cls.__fields__.keys()
            filtered_context = {k: v for k, v in context.items() if k in valid_keys}
            
            # Ensure 'input' is present if required
            if "input" not in filtered_context and "input" in valid_keys:
                filtered_context["input"] = context.get("query", context.get("text", ""))

            mission_input = input_cls(**filtered_context)

            # 3. Execute Mission
            logger.info(f"Registry: Dispatching '{name}' mission.")
            return await agent.execute(mission_input, lang=lang)

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
