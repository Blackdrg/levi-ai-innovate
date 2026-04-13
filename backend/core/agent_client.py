"""
Sovereign Agent Client v15.0.0.
Handles mTLS 1.3 secure communication with the distributed agent swarm.
"""

import os
import logging
import asyncio
import json
import ssl
import aiohttp
from typing import Dict, Any, Optional

from backend.agents.registry import AGENT_REGISTRY
from backend.core.orchestrator_types import ToolResult
from backend.core.agent_config import AgentConfig

logger = logging.getLogger(__name__)

class SovereignAgentClient:
    """
    mTLS-secured client for communicating with remote LEVI-AI agents.
    """

    def __init__(self):
        self.cert_dir = os.getenv("CERTS_DIR", "certs")
        self.client_cert = os.path.join(self.cert_dir, "client.pem")
        self.client_key = os.path.join(self.cert_dir, "client-key.pem")
        self.ca_cert = os.path.join(self.cert_dir, "ca.pem")
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        Creates a mutual TLS 1.3 context.
        """
        try:
            if not os.path.exists(self.client_cert):
                logger.warning(f"[AgentClient] Client cert not found at {self.client_cert}. Using insecure fallback.")
                return None

            ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=self.ca_cert)
            ctx.load_cert_chain(certfile=self.client_cert, keyfile=self.client_key)
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = False # Development flexibility
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            return ctx
        except Exception as e:
            logger.error(f"[AgentClient] SSL Context Error: {e}")
            return None

    async def call_agent(
        self, 
        agent_id: str, 
        params: Dict[str, Any], 
        context: Dict[str, Any], 
        timeout: float = 30.0
    ) -> ToolResult:
        """
        Dispatches a secure request to the specified agent.
        """
        config = AGENT_REGISTRY.get(agent_id)
        if not config or not isinstance(config, AgentConfig):
            return ToolResult(success=False, error=f"Agent {agent_id} not registered", agent=agent_id)

        endpoint = f"{config.mtls_endpoint}/execute"
        headers = {
            "X-Sovereign-Internal": os.getenv("INTERNAL_SERVICE_KEY", "dev-secret"),
            "Content-Type": "application/json"
        }

        try:
            connector = aiohttp.TCPConnector(ssl=self._ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    endpoint,
                    json={"params": params, "context": context},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status != 200:
                        detail = await response.text()
                        return ToolResult(success=False, error=f"Agent Error ({response.status}): {detail}", agent=agent_id)
                    
                    data = await response.json()
                    return ToolResult(
                        success=data.get("success", False),
                        message=data.get("message", ""),
                        agent=agent_id,
                        data=data.get("data", {}),
                        latency_ms=data.get("latency_ms", 0)
                    )
        except Exception as e:
            logger.error(f"[AgentClient] mTLS Handshake/Dispatch failure to {agent_id}: {e}")
            return ToolResult(success=False, error=f"Secure dispatch failure: {str(e)}", agent=agent_id)

# Global client singleton
agent_client = SovereignAgentClient()
