"""
Sovereign Cloud Burst Agent v14.0.
Handles dynamic task offloading to cloud providers when local VRAM is saturated.
Ensures zero-downtime mission execution by bridging the Sovereign core with cloud-burst nodes.
"""

import logging
from typing import Dict, Any
from backend.core.cloud_fallback import CloudFallbackProxy
from backend.core.orchestrator_types import AgentResult

logger = logging.getLogger(__name__)

class CloudBurstAgent:
    """
    Sovereign v14.0: Hybrid Cloud Transition Layer.
    Only invoked when LOCAL_VRAM is exhausted.
    """
    
    def __init__(self):
        self.proxy = CloudFallbackProxy()

    async def run(self, agent_name: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """Dispatches the agent task to the most appropriate cloud provider."""
        logger.info(f"[CloudBurst] Offloading {agent_name} mission to cloud provider...")
        
        # 1. Select Cloud Tier (Heuristic)
        # L3/L4 missions usually go to Groq or GPT-4o
        target_provider = "groq" if agent_name in ["chat_agent", "code_agent"] else "openai"
        
        try:
            # 2. Execute via Cloud Proxy
            cloud_res = await self.proxy.dispatch_mission(
                target_provider=target_provider,
                agent_name=agent_name,
                payload=params
            )
            
            # 3. Standardize Result
            return AgentResult(
                success=cloud_res.get("success", False),
                message=cloud_res.get("response", ""),
                data={
                    **cloud_res.get("data", {}),
                    "burst_active": True,
                    "provider": target_provider
                },
                agent=f"{agent_name} (Cloud Burst)",
                latency_ms=cloud_res.get("latency_ms", 0.0)
            )
            
        except Exception as e:
            logger.error(f"[CloudBurst] Critical offload failure: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                message="The Cloud Burst link was severed during saturation.",
                agent=agent_name
            )
