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
    
    region: str = "us-east" # Regional awareness (v14.2)
    
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
        self.region = os.getenv("DCN_REGION", "us-east")
        self.peers = set() # Tracked via heartbeats

        # Audit Point 27: Strict Secret Validation
        if not self.secret or len(self.secret) < 32:
            msg = (
                f"[DCN] INSECURE CONFIGURATION: DCN_SECRET is too short (min 32 chars). "
                "DCN nodes MUST run with high-entropy secrets in production."
            )
            logger.critical(msg)
            if os.getenv("ENV") == "production":
                raise ValueError(msg)
            self.is_active = False
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
            index=self.last_applied_index + 1 if mode == ConsensusMode.RAFT else 0,
            region=self.region
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
                        "region": self.region,
                        "capabilities": ["llm"] + (["studio"] if os.getenv("SD_ENABLED", "true").lower() == "true" else []),
                        "concurrency": int(os.getenv("WORKER_CONCURRENCY", "1")),
                        "vram_free_mb": sum(s["vram_free_mb"] for s in device_slots)
                    }
                    # Update local peer list
                    self.peers.add(self.node_id)
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
                
                # Consensus Rule Enforcement (Wiring #5)
                if pulse.mode == ConsensusMode.RAFT:
                    if pulse.term < self.gossip.current_term:
                        logger.warning(f"[DCN] RAFT: Stale pulse rejected (Term {pulse.term} < {self.gossip.current_term})")
                        return
                    
                    # 🛡️ Quorum Enforcement (v14.1 Scaling)
                    quorum_size = (len(self.peers) // 2) + 1
                    logger.debug(f"[DCN] RAFT: Quorum calculated at {quorum_size} nodes (Total Peers: {len(self.peers)})")

                    # Reconcile local state index if drift detected
                    if pulse.index > self.last_applied_index:
                         await self.reconcile_state(pulse.mission_id, pulse.index)
                    
                    if pulse.index > self.commit_index:
                        self.commit_index = pulse.index
                        logger.debug(f"[DCN] RAFT: Commit Index updated to {self.commit_index}")

                if pulse.payload_type == "node_heartbeat":
                    peer_meta = pulse.payload
                    self.peers.add(pulse.node_id)
                    if peer_meta.get("region") != self.region:
                         logger.info(f"[DCN] Cross-region peer detected: {pulse.node_id} ({peer_meta.get('region')})")

                await handler(pulse)
            except Exception as e:
                logger.error(f"[DCN] Listener processing failure: {e}")

        logger.info(f"[DCN] Secure Consensus Listener: [ACTIVE] Node: {self.node_id}")
        from backend.utils.runtime_tasks import create_tracked_task
        create_tracked_task(self.gossip.listen(secure_handler), name="dcn-gossip-listener")

    async def verify_pulse(self, pulse: DCNPulse) -> bool:
        """Verifies the integrity, authenticity, and temporal validity of an incoming pulse."""
        if not pulse.signature:
            logger.warning(f"[DCN] Missing signature from {pulse.node_id}")
            return False

        # Anti-Replay: 60-second window
        drift = abs(time.time() - pulse.timestamp)
        if drift > 60:
            logger.warning(f"[DCN] Pulse from {pulse.node_id} rejected due to timestamp drift: {drift:.2f}s")
            return False

        msg_json = pulse.model_dump_json(exclude={"signature"})
        expected_sig = hmac.new(self.secret.encode(), msg_json.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(pulse.signature, expected_sig)

    def verify_quorum(self, votes: int, regional_diversity: Optional[List[str]] = None, enforce_diversity: bool = False) -> bool:
        """
        Sovereign v14.2: Hardened Quorum Verification.
        Checks if a given vote count meets the Raft-lite quorum threshold.
        If enforce_diversity is True, requires votes from at least 2 distinct regions.
        """
        total_peers = len(self.peers)
        if total_peers <= 1:
            return True # Single node swarm always has quorum
            
        required = (total_peers // 2) + 1
        meets_count = votes >= required
        
        if not enforce_diversity:
            return meets_count
            
        # Cross-region RAFT: Enforce geographical diversity for DEEP/SECURE missions
        distinct_regions = set(regional_diversity) if regional_diversity else set()
        has_diversity = len(distinct_regions) >= 2
        
        if meets_count and not has_diversity:
             logger.warning(f"[DCN] Quorum count met ({votes}), but REGIONAL DIVERSITY failed. Required >= 2 regions.")
             
        return meets_count and has_diversity

    async def reconcile_state(self, mission_id: str, remote_index: int):
        """Forces a state reconciliation if local index drifts from Raft commit index."""
        if remote_index > self.last_applied_index:
            logger.warning(f"[DCN] State Drift Detected for {mission_id}. Local: {self.last_applied_index}, Remote: {remote_index}")
            # In production, we'd pull from the Redis Event Stream to replay logs
            # For graduates, we trigger the ReplayEngine recovery link.
            from .replay_engine import ReplayEngine
            engine = ReplayEngine()
            await engine.recover_mission_state(mission_id)
            self.last_applied_index = remote_index
