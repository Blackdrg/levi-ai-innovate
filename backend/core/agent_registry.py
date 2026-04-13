# backend/core/agent_registry.py
import logging
import jsonschema
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class AgentCapability:
    name: str
    agent_type: str
    input_schema: dict
    output_schema: dict
    timeout_seconds: int = 60
    max_retries: int = 3
    is_sovereign: bool = True

class AgentRegistry:
    """
    Sovereign v15.0 Agent Registry.
    Enforces strict TEC (Task Execution Contract) via JSON Schema.
    """
    _agents: Dict[str, AgentCapability] = {}

    @classmethod
    def register(cls, name: str, capability: AgentCapability):
        cls._agents[name.lower()] = capability
        logger.info(f"[Registry] Registered agent: {capability.name} ({capability.agent_type})")

    @classmethod
    def get_agent(cls, name: str) -> Optional[AgentCapability]:
        return cls._agents.get(name.lower())

    @classmethod
    async def validate_input(cls, agent_name: str, payload: dict) -> bool:
        agent = cls.get_agent(agent_name)
        if not agent:
            logger.warning(f"[Registry] Agent {agent_name} not found for validation.")
            return False
        try:
            jsonschema.validate(instance=payload, schema=agent.input_schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"[Registry] Input validation FAILED for {agent_name}: {e.message}")
            return False

# Default Agent Configurations (Hardened v15.0)
DEFAULT_AGENTS = {
    "scout": AgentCapability(
        name="Scout",
        agent_type="search",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 3},
                "provider": {"type": "string", "enum": ["google", "tavily", "brave"], "default": "google"}
            },
            "required": ["query"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "results": {"type": "array"},
                "total": {"type": "integer"}
            }
        }
    ),
    "artisan": AgentCapability(
        name="Artisan",
        agent_type="coder",
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string", "enum": ["python", "javascript", "bash"]}
            },
            "required": ["code", "language"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "exit_code": {"type": "integer"}
            }
        }
    ),
    "librarian": AgentCapability(
        name="Librarian",
        agent_type="research",
        input_schema={
            "type": "object",
            "properties": {
                "file_id": {"type": "string"},
                "depth": {"type": "string", "enum": ["surface", "deep", "exhaustive"]}
            },
            "required": ["file_id"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "citations": {"type": "array"}
            }
        }
    )
}

# Initialize with defaults
for name, cap in DEFAULT_AGENTS.items():
    AgentRegistry.register(name, cap)
