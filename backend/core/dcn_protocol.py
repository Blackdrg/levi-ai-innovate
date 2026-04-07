"""
Sovereign DCN (Distributed Cognitive Network) Protocol v13.1.0.
Handles HMAC-signed cognitive gossip and localized Kubernetes service discovery.
"""

import os
import hmac
import hashlib
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DCNPulse(BaseModel):
    """
    The atomic unit of exchange in the DCN.
    """
    node_id: str
    mission_id: str
    payload_type: str # 'insight', 'artifact', 'heartbeat'
    payload: str # Base64 zlib blob
    signature: str

from .dcn.gossip import DCNGossip

class DCNProtocol:
    """
    Sovereign DCN Orchestrator v2.0.
    Manages peering, gossip, and Sybil resistance via Redis Streams.
    """
    
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or os.getenv("DCN_NODE_ID", "node_alpha")
        self.secret = os.getenv("DCN_SECRET", "")
        self.is_active = False
        self.gossip: Optional[DCNGossip] = None

        # Audit Point 27: Strict Secret Validation
        if not self.secret or len(self.secret) < 32:
            logger.warning(
                f"[DCN] INSECURE CONFIGURATION: DCN_SECRET is {'missing' if not self.secret else 'too short'}. "
                "DCN gossip will remain OFFLINE to prevent unauthenticated pulse injection."
            )
        else:
            self.is_active = True
            logger.info(f"[DCN] Protocol v13.1.0 Active. Node: {self.node_id}")
            self.gossip = DCNGossip()

    async def broadcast_gossip(self, mission_id: str, payload: Any, pulse_type: str = "cognitive_gossip"):
        """Gossips a cognitive pulse to all nodes via Redis Streams."""
        if not self.is_active or not self.gossip:
            return

        pulse_payload = {
            "mission_id": mission_id,
            "data": payload,
            "type": pulse_type
        }
        await self.gossip.broadcast_pulse(pulse_payload)

    async def start_heartbeat(self, interval: int = 30):
        """Starts a background task that broadcasts a node heartbeat."""
        if not self.is_active or not self.gossip:
            return

        logger.info(f"[DCN] Autonomous Heartbeat: [ENABLED] ({interval}s interval)")
        
        async def heartbeat_loop():
            while self.is_active:
                try:
                    # Collect node metadata
                    import psutil
                    metadata = {
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_percent": psutil.virtual_memory().percent,
                        "node_role": os.getenv("NODE_ROLE", "worker"),
                        "concurrency": int(os.getenv("WORKER_CONCURRENCY", "1"))
                    }
                    
                    await self.broadcast_gossip(
                        mission_id="swarm_pulse", 
                        payload=metadata, 
                        pulse_type="node_heartbeat"
                    )
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"[DCN] Heartbeat error: {e}")
                    await asyncio.sleep(10) # Wait before retry

        asyncio.create_task(heartbeat_loop())

    async def start_listener(self, handler: Callable):
        """Starts the background gossip listener."""
        if self.is_active and self.gossip:
            asyncio.create_task(self.gossip.listen(handler))

    async def verify_pulse(self, pulse: DCNPulse) -> bool:
        """
        Verifies the integrity and authenticity of an incoming pulse.
        (Legacy support for manual verification if needed)
        """
        expected_msg = f"{pulse.node_id}:{pulse.mission_id}:{pulse.payload}".encode()
        expected_sig = hmac.new(self.secret.encode(), expected_msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(pulse.signature, expected_sig)
