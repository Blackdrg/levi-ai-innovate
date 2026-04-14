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
    required_role: str = "user" # RBAC: guest, user, admin, developer

from .agent_config import AgentConfig

class AgentRegistry:
    """
    Sovereign v15.0 Agent Registry.
    Enforces strict TEC (Task Execution Contract) and hierarchical configurations.
    """
    _agents: Dict[str, AgentCapability] = {}
    _configs: Dict[str, AgentConfig] = {}

    @classmethod
    def register(cls, name: str, capability: AgentCapability, config: Optional[AgentConfig] = None):
        cls._agents[name.lower()] = capability
        if config:
            cls._configs[name.lower()] = config
        logger.info(f"[Registry] Registered agent: {capability.name} ({capability.agent_type})")

    @classmethod
    def get_agent(cls, name: str) -> Optional[AgentCapability]:
        return cls._agents.get(name.lower())

    @classmethod
    def get_config(cls, name: str) -> Optional[AgentConfig]:
        return cls._configs.get(name.lower())

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

    @classmethod
    async def graduate_rule(cls, rule: Dict[str, Any]):
        """
        Sovereign v15.2: Dynamic Rule Graduation.
        Promotes a successful evolutionary pattern to a deterministic agent capability.
        """
        import time
        name = rule.get("tag", f"evolved_{int(time.time())}")
        logger.info(f"🚀 [Registry] Graduating evolutionary rule to core capability: {name}")
        
        # Construct a specialized capability for the evolved rule
        cap = AgentCapability(
            name=name,
            agent_type="evolved_logic",
            input_schema=rule.get("input_schema", {"type": "object"}),
            output_schema=rule.get("output_schema", {"type": "object"}),
            is_sovereign=True,
            required_role="user"
        )
        
        cls.register(name, cap)

# Default Agent Configurations (Hardened v15.0 Swarm)
DEFAULT_AGENTS = {
    "scout": AgentCapability(
        name="Scout",
        agent_type="search",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        output_schema={"type": "object"}
    ),
    "artisan": AgentCapability(
        name="Artisan",
        agent_type="coder",
        input_schema={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        required_role="developer",
        output_schema={"type": "object"}
    ),
    "librarian": AgentCapability(
        name="Librarian",
        agent_type="research",
        input_schema={"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]},
        output_schema={"type": "object"}
    ),
    "critic": AgentCapability(
        name="Critic",
        agent_type="validation",
        input_schema={"type": "object", "properties": {"draft": {"type": "string"}}, "required": ["draft"]},
        output_schema={"type": "object"}
    ),
    "architect": AgentCapability(
        name="Architect",
        agent_type="planner",
        input_schema={"type": "object", "properties": {"objective": {"type": "string"}}, "required": ["objective"]},
        output_schema={"type": "object"}
    ),
    "chronicler": AgentCapability(
        name="Chronicler",
        agent_type="memory",
        input_schema={"type": "object", "properties": {"event": {"type": "string"}}, "required": ["event"]},
        output_schema={"type": "object"}
    ),
    "sentinel": AgentCapability(
        name="Sentinel",
        agent_type="security",
        input_schema={"type": "object", "properties": {"payload": {"type": "string"}}, "required": ["payload"]},
        required_role="admin",
        output_schema={"type": "object"}
    ),
    "vision": AgentCapability(
        name="Vision",
        agent_type="video",
        input_schema={"type": "object", "properties": {"source": {"type": "string"}}, "required": ["source"]},
        output_schema={"type": "object"}
    ),
    "echo": AgentCapability(
        name="Echo",
        agent_type="audio",
        input_schema={"type": "object", "properties": {"audio_data": {"type": "string"}}, "required": ["audio_data"]},
        output_schema={"type": "object"}
    ),
    "analyst": AgentCapability(
        name="Analyst",
        agent_type="analysis",
        input_schema={"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]},
        output_schema={"type": "object"}
    ),
    "curator": AgentCapability(
        name="Curator",
        agent_type="graph",
        input_schema={"type": "object", "properties": {"triplets": {"type": "array"}}, "required": ["triplets"]},
        output_schema={"type": "object"}
    ),
    "messenger": AgentCapability(
        name="Messenger",
        agent_type="notification",
        input_schema={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
        output_schema={"type": "object"}
    ),
    "consensus": AgentCapability(
        name="Consensus",
        agent_type="consensus",
        input_schema={"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]},
        output_schema={"type": "object"}
    ),
    "policy": AgentCapability(
        name="Policy",
        agent_type="optimization",
        input_schema={"type": "object", "properties": {"mission_id": {"type": "string"}}, "required": ["mission_id"]},
        output_schema={"type": "object"}
    ),
    "dreamer": AgentCapability(
        name="Dreamer",
        agent_type="evolution",
        input_schema={"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
        output_schema={"type": "object"}
    ),
    "sovereign": AgentCapability(
        name="Sovereign",
        agent_type="core",
        input_schema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
        output_schema={"type": "object"}
    )
}

# Initialize with defaults
for name, cap in DEFAULT_AGENTS.items():
    config = AgentConfig(
        name=cap.name,
        type=cap.agent_type,
        mtls_endpoint=f"https://agent-{name}.internal:5001",
        timeout_ms=cap.timeout_seconds * 1000,
        max_retries=cap.max_retries
    )
    AgentRegistry.register(name, cap, config=config)
