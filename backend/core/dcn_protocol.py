"""
Sovereign DCN (Distributed Cognitive Network) Protocol v14.1.0.
Hybrid Consensus: 
- Gossip + LWW for scaling/discovery.
- Raft-lite for mission truth and state reconciliation.
"""

import os
import hmac
import hashlib
import logging
import asyncio
import json
import time
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from pydantic import BaseModel, Field
from .v13.vram_guard import VRAMGuard
from .dcn.load_balancer import dcn_balancer

logger = logging.getLogger(__name__)

class ConsensusMode(str, Enum):
    GOSSIP = "gossip" # Eventual consistency, high availability
    RAFT = "raft"     # Strong consistency, mission truth

class DCNPulse(BaseModel):
    """
    The atomic unit of exchange in the DCN.
    Now includes Raft semantics for mission truth.
    """
    node_id: str
    mission_id: str
    payload_type: str 
    payload: Any
    mode: ConsensusMode = ConsensusMode.GOSSIP
    
    # Raft Semantics (v14.1)
    term: int = 0
    index: int = 0
    prev_log_index: int = 0
    prev_log_term: int = 0
    
    signature: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

from .dcn.gossip import DCNGossip

class DCNProtocol:
    """
    Sovereign DCN Orchestrator v2.1 (Graduated).
    Manages peering, consensus, and state reconciliation across the cognitive swarm.
    
    Failure Model:
    - Omission: Network packet loss or node timeout.
    - Partition: Network split (handled by Quorum + Term checks).
    - Crash: Node stops (handled by Lease expiration).
    """
    
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or os.getenv("DCN_NODE_ID", "node_alpha")
        self.secret = os.getenv("DCN_SECRET", "")
        self.is_active = False
        self.gossip: Optional[DCNGossip] = None
        self.vram_guard = VRAMGuard()
        self.last_applied_index = 0
        self.commit_index = 0

        # Audit Point 27: Strict Secret Validation
        if not self.secret or len(self.secret) < 32:
            logger.warning(
                f"[DCN] INSECURE CONFIGURATION: DCN_SECRET is too short. "
                "DCN gossip will remain OFFLINE to prevent unauthenticated injection."
            )
        else:
            self.is_active = True
            logger.info(f"[DCN] Protocol v14.1.0 Active (Hybrid Consensus). Node: {self.node_id}")
            self.gossip = DCNGossip()

    def sign_pulse(self, mission_id: str, payload: Any, mode: ConsensusMode = ConsensusMode.GOSSIP) -> DCNPulse:
        """Signs a pulse with the node's secret and consensus metadata."""
        pulse = DCNPulse(
            node_id=self.node_id,
            mission_id=mission_id,
            payload_type="mission_state" if mode == ConsensusMode.RAFT else "cognitive_gossip",
            payload=payload,
            mode=mode,
            term=self.gossip.current_term if self.gossip else 0,
            index=self.last_applied_index + 1 if mode == ConsensusMode.RAFT else 0
        )
        
        # We need a predictable string for signing. Using model_dump_json is good but exclude signature.
        msg_json = pulse.model_dump_json(exclude={"signature"})
        pulse.signature = hmac.new(
            self.secret.encode(),
            msg_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return pulse

    async def broadcast_mission_truth(self, mission_id: str, outcome: Dict[str, Any]):
        """Broadcasts definitive mission results using Raft-lite consensus."""
        if not self.is_active or not self.gossip:
            return
            
        pulse = self.sign_pulse(mission_id, outcome, mode=ConsensusMode.RAFT)
        await self.gossip.broadcast_pulse(pulse.model_dump())
        self.last_applied_index = pulse.index
        logger.info(f"[DCN] Mission Truth Propagated: {mission_id} (Index: {pulse.index})")

    async def broadcast_gossip(self, mission_id: str, payload: Any, pulse_type: str = "cognitive_gossip"):
        """Gossips a non-critical cognitive pulse using eventual consistency."""
        if not self.is_active or not self.gossip:
            return

        pulse = self.sign_pulse(mission_id, payload, mode=ConsensusMode.GOSSIP)
        pulse.payload_type = pulse_type
        await self.gossip.broadcast_pulse(pulse.model_dump())

    async def start_heartbeat(self, interval: int = 30):
        """Starts a background task that broadcasts a node heartbeat (Gossip mode)."""
        if not self.is_active or not self.gossip:
            return

        logger.info(f"[DCN] Autonomous Discovery Heartbeat: [ENABLED] ({interval}s interval)")
        
        async def heartbeat_loop():
            while self.is_active:
                try:
                    import psutil
                    device_slots = await self.vram_guard.get_device_slots(force_refresh=True)
                    metadata = {
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_percent": psutil.virtual_memory().percent,
                        "node_role": os.getenv("NODE_ROLE", "worker"),
                        "capabilities": ["llm"] + (["studio"] if os.getenv("SD_ENABLED", "true").lower() == "true" else []),
                        "concurrency": int(os.getenv("WORKER_CONCURRENCY", "1")),
                        "vram_free_mb": sum(s["vram_free_mb"] for s in device_slots)
                    }
                    dcn_balancer.register_node_heartbeat(self.node_id, metadata)
                    await self.broadcast_gossip(mission_id="swarm_pulse", payload=metadata, pulse_type="node_heartbeat")
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"[DCN] Heartbeat error: {e}")
                    await asyncio.sleep(10)

        from backend.utils.runtime_tasks import create_tracked_task
        create_tracked_task(heartbeat_loop(), name="dcn-heartbeat")

    async def start_listener(self, handler: Callable):
        """Starts the background consensus listener with HMAC enforcement."""
        if not self.is_active or not self.gossip:
            return

        async def secure_handler(pulse_raw: Dict[str, Any]):
            try:
                # 🛡️ HMAC-SHA256 Verification
                pulse = DCNPulse(**pulse_raw)
                if not await self.verify_pulse(pulse):
                    logger.warning(f"[DCN] Dropping unauthenticated pulse from {pulse.node_id}")
                    return
                
                # Consensus Rule Enforcement
                if pulse.mode == ConsensusMode.RAFT:
                    if pulse.term < self.gossip.current_term:
                        logger.warning(f"[DCN] RAFT: Stale pulse rejected (Term {pulse.term} < {self.gossip.current_term})")
                        return
                    # Reconcile local state index
                    if pulse.index > self.commit_index:
                        self.commit_index = pulse.index
                        logger.debug(f"[DCN] RAFT: Commit Index updated to {self.commit_index}")

                await handler(pulse)
            except Exception as e:
                logger.error(f"[DCN] Listener processing failure: {e}")

        logger.info(f"[DCN] Secure Consensus Listener: [ACTIVE] Node: {self.node_id}")
        from backend.utils.runtime_tasks import create_tracked_task
        create_tracked_task(self.gossip.listen(secure_handler), name="dcn-gossip-listener")

    async def verify_pulse(self, pulse: DCNPulse) -> bool:
        """Verifies the integrity and authenticity of an incoming pulse."""
        msg_json = pulse.model_dump_json(exclude={"signature"})
        expected_sig = hmac.new(self.secret.encode(), msg_json.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(pulse.signature, expected_sig)
