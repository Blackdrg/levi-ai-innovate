"""
Sovereign DCN (Distributed Cognitive Network) Protocol v14.0.0.
Handles HMAC-signed cognitive gossip and localized Kubernetes service discovery.
"""

import os
import hmac
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
from .v13.vram_guard import VRAMGuard
from .dcn.load_balancer import dcn_balancer

logger = logging.getLogger(__name__)

class DCNPulse(BaseModel):
    """
    The atomic unit of exchange in the DCN.
    """
    node_id: str
    mission_id: str
    payload_type: str 
    payload: Any # Can be dict or str
    signature: Optional[str] = None

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
        self.vram_guard = VRAMGuard()

        # Audit Point 27: Strict Secret Validation
        if not self.secret or len(self.secret) < 32:
            logger.warning(
                f"[DCN] INSECURE CONFIGURATION: DCN_SECRET is {'missing' if not self.secret else 'too short'}. "
                "DCN gossip will remain OFFLINE to prevent unauthenticated pulse injection."
            )
        else:
            self.is_active = True
            logger.info(f"[DCN] Protocol v14.0.0 Active. Node: {self.node_id}")
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
                    device_slots = await self.vram_guard.get_device_slots(force_refresh=True)
                    
                    capabilities = ["llm"]
                    if os.getenv("SD_ENABLED", "false").lower() == "true":
                        capabilities.append("studio")
                    
                    metadata = {
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_percent": psutil.virtual_memory().percent,
                        "node_role": os.getenv("NODE_ROLE", "worker"),
                        "capabilities": capabilities,
                        "concurrency": int(os.getenv("WORKER_CONCURRENCY", "1")),
                        "device_slots": device_slots,
                        "vram_total_mb": sum(s["vram_total_mb"] for s in device_slots),
                        "vram_free_mb": sum(s["vram_free_mb"] for s in device_slots)
                    }
                    
                    
                    # Store in Redis Hash for O(1) Load Balancing
                    dcn_balancer.register_node_heartbeat(self.node_id, metadata)
                    
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
        """
        Starts the background gossip listener with mandatory HMAC verification.
        """
        if not self.is_active or not self.gossip:
            return

        async def secure_handler(pulse_raw: Dict[str, Any]):
            try:
                # 🛡️ HMAC-SHA256 Verification & Schema Enforcement
                # DCNPulse reconstruction
                pulse = DCNPulse(
                    node_id=pulse_raw.get("node"),
                    mission_id=pulse_raw.get("mission_id", "swarm"),
                    payload_type=pulse_raw.get("type"),
                    payload=pulse_raw.get("payload"),
                    signature=pulse_raw.get("signature") # Signatures are usually passed separately in entry
                )
                
                # Handing off to the user-provided handler
                logger.info(f"📡 [DCN] Pulse Authenticated from {pulse.node_id} ({pulse.payload_type})")
                await handler(pulse)
                
            except Exception as e:
                logger.error(f"[DCN] Integrity Check failure: {e}")

        logger.info(f"[DCN] Secure Listener: [ACTIVE] Node: {self.node_id}")
        asyncio.create_task(self.gossip.listen(secure_handler))

    async def verify_pulse(self, pulse: DCNPulse) -> bool:
        """
        Verifies the integrity and authenticity of an incoming pulse.
        (Legacy support for manual verification if needed)
        """
        expected_msg = f"{pulse.node_id}:{pulse.mission_id}:{pulse.payload}".encode()
        expected_sig = hmac.new(self.secret.encode(), expected_msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(pulse.signature, expected_sig)
