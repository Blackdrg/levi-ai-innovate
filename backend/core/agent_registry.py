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
    Sovereign v22.1 Agent Registry.
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

# ── The Sovereign v22.1 Swarm (16 Nodes) ───────────────────────────

DEFAULT_AGENTS = {
    "sovereign": AgentCapability(
        name="Sovereign",
        agent_type="core",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        required_role="admin"
    ),
    "architect": AgentCapability(
        name="Architect",
        agent_type="planner",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "artisan": AgentCapability(
        name="Artisan",
        agent_type="builder",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        required_role="developer"
    ),
    "analyst": AgentCapability(
        name="Analyst",
        agent_type="analysis",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "critic": AgentCapability(
        name="Critic",
        agent_type="gatekeeper",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "sentinel": AgentCapability(
        name="Sentinel",
        agent_type="security",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "historian": AgentCapability(
        name="Historian",
        agent_type="chronicler",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "forensic": AgentCapability(
        name="Forensic",
        agent_type="auditor",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        required_role="admin"
    ),
    "nomad": AgentCapability(
        name="Nomad",
        agent_type="bridge",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "thermal": AgentCapability(
        name="Thermal",
        agent_type="guardian",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "epistemic": AgentCapability(
        name="Epistemic",
        agent_type="resonator",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "pulse": AgentCapability(
        name="Pulse",
        agent_type="sync",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "shield": AgentCapability(
        name="Shield",
        agent_type="privacy",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "shadow": AgentCapability(
        name="Shadow",
        agent_type="redundancy",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "hive": AgentCapability(
        name="Hive",
        agent_type="swarm",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    ),
    "genesis": AgentCapability(
        name="Genesis",
        agent_type="bootstrapper",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        required_role="admin"
    )
}

# Initialize with defaults
for name, cap in DEFAULT_AGENTS.items():
    config = AgentConfig(
        name=cap.name,
        type=cap.agent_type,
        mtls_endpoint=f"https://agent-{name}.internal:5001",
        timeout_ms=cap.timeout_seconds * 1000,
        max_retries=cap.max_retries,
        capabilities=[cap.agent_type]
    )
    AgentRegistry.register(name, cap, config=config)
