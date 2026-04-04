from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class PromptRegistry:
    """
    Sovereign v13.0: Centralized Prompt Versioning & Governance.
    Allows for structured A/B testing and rollbacks across the agent swarm.
    """
    
    _PROMPTS = {
        "the_researcher": {
            "v1.0": "You are a specialized deep-web researcher. Extract atomic facts and cite evidence.",
            "v1.1": "You are the LEVI Researcher v1.1. Analyze intent before searching. CITATIONS MANDATORY."
        },
        "the_artisan": {
            "v1.0": "You are a software engineer. Write clean code and use the sandbox.",
            "v1.1": "You are the LEVI Code Artisan. All execution MUST be isolated. Include tests."
        },
        "the_brain": {
            "v1.0": "You are the LEVI Sovereign Brain. Orchestrate agents to fulfill the mission.",
            "v1.1": "You are the Absolute Monolith Brain v13.0. Enforce DAG integrity and fidelity S scores."
        }
    }
    
    _DEFAULT_VERSIONS = {
        "the_researcher": "v1.1",
        "the_artisan": "v1.1",
        "the_brain": "v1.1"
    }

    @classmethod
    def get_prompt(cls, agent_id: str, version: Optional[str] = None) -> str:
        """Retrieves a versioned prompt template."""
        if agent_id not in cls._PROMPTS:
            logger.warning(f"No prompt template found for agent '{agent_id}'. Using standard fallback.")
            return "You are a Sovereign AI agent. Complete the mission with high fidelity."
            
        target_version = version or cls._DEFAULT_VERSIONS.get(agent_id, "v1.0")
        if target_version not in cls._PROMPTS[agent_id]:
            logger.warning(f"Version '{target_version}' not found for agent '{agent_id}'. Rolling back to default.")
            target_version = cls._DEFAULT_VERSIONS[agent_id]
            
        return cls._PROMPTS[agent_id][target_version]

    @classmethod
    def list_registry(cls) -> Dict[str, Any]:
        """Returns the current registry for architectural auditability."""
        return {
            "prompts": cls._PROMPTS,
            "defaults": cls._DEFAULT_VERSIONS
        }
