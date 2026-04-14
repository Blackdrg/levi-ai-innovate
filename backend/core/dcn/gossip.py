import asyncio
import json
import time
import hmac
import hashlib
import logging
import random
import os
from typing import Set, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from backend.db.redis import r_async as redis_async, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

@dataclass
class GossipPulse:
    node_id: str
    term: int  # Raft term
    facts: Dict[str, Any]
    timestamp: float
    signature: str

class DCNGossip:
    """
    Sovereign DCN Gossip Implementation v16.0.
    Satisfies DCNProtocol interface while providing decentralized state synchronization.
    """
    def __init__(self, node_id: Optional[str] = None, interval: int = 30):
        self.node_id = node_id or os.getenv("DCN_NODE_ID", "node_alpha")
        self.interval = interval
        self.secret = os.getenv("DCN_SECRET", "sovereign_fallback_secret_32_chars")
        self.r = redis_async if HAS_REDIS_ASYNC else None
        self.is_running = True
        self.local_state = {}
        self.peers = set()
        self.term = 0
        self.leader = None

    async def broadcast_pulse(self, pulse_data: Dict[str, Any]):
        """Broadcasts a pulse to the network via Redis Stream."""
        if not self.r: return
        try:
            # Add to main DCN stream
            await self.r.xadd("dcn:stream:pulse", {"data": json.dumps(pulse_data)})
            logger.debug(f"[DCNGossip] Pulse broadcasted: {pulse_data.get('payload_type')}")
        except Exception as e:
            logger.error(f"[DCNGossip] Broadcast failure: {e}")

    async def listen(self, handler: Callable):
        """Listens for incoming pulses from the Redis Stream."""
        if not self.r: return
        
        logger.info(f"🛰️ [DCNGossip] Listening for pulses on node {self.node_id}")
        last_id = "$"
        
        while self.is_running:
            try:
                # Read from stream
                resp = await self.r.xread({"dcn:stream:pulse": last_id}, count=10, block=5000)
                if not resp: continue
                
                for stream, messages in resp:
                    for mid, data in messages:
                        last_id = mid
                        pulse_raw = json.loads(data[b"data"])
                        # Don't process our own pulses in the listener logic (usually handled by DCNProtocol)
                        await handler(pulse_raw)
            except Exception as e:
                logger.error(f"[DCNGossip] Listen error: {e}")
                await asyncio.sleep(5)

    async def heartbeat(self):
        """Autonomous state sync heartbeat."""
        while self.is_running:
            try:
                pulse = {
                    "node_id": self.node_id,
                    "payload_type": "gossip_state_sync",
                    "payload": self.local_state,
                    "timestamp": time.time(),
                    "term": self.term
                }
                await self.broadcast_pulse(pulse)
            except Exception as e:
                logger.warning(f"[DCNGossip] Heartbeat failed: {e}")
            await asyncio.sleep(self.interval)

    def stop_gossip_hub(self):
        """Shutdown handler."""
        self.is_running = False

class GossipProtocol(DCNGossip):
    """Legacy alias for backward compatibility with recent edits."""
    def __init__(self, node_id: str, peers: Set[str], interval: int = 30, secret: str = "sovereign_fallback_secret", db: Any = None):
        super().__init__(node_id=node_id, interval=interval)
        self.peers = peers
        self.secret = secret
        self.db = db

    def _sign_pulse(self, data: Dict) -> str:
        msg = json.dumps(data, sort_keys=True)
        return hmac.new(self.secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
