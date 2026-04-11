# backend/core/agent_config.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class AgentConfig:
    """
    Sovereign v14.2: Hierarchical Agent Configuration.
    Defines security, networking, and isolation parameters for cognitive agents.
    """
    name: str
    type: str  # scout, artisan, researcher, etc.
    mtls_endpoint: str  # e.g., "https://localhost:5001"
    timeout_ms: int = 30000
    max_retries: int = 2
    allowed_tools: List[str] = field(default_factory=list)
    
    # Sandbox Configuration (Wiring #3)
    sandbox_image: str = "python:3.10-slim"
    memory_limit_mb: int = 512
    cpu_cores: float = 1.0
    
    # Metadata for swarm routing
    capabilities: List[str] = field(default_factory=list)
    region: str = "dev-local"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "mtls_endpoint": self.mtls_endpoint,
            "timeout_ms": self.timeout_ms,
            "sandbox_image": self.sandbox_image,
            "capabilities": self.capabilities
        }
