# backend/core/dcn/peer_discovery.py
import asyncio
import json
import time
import random
import hmac
import hashlib
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DCNPeer(BaseModel):
    node_id: str
    host: str
    port: int
    region: str
    last_heartbeat: float = 0.0
    status: str = "UNKNOWN"

class HybridGossip:
    """
    Sovereign DCN Hybrid Gossip v15.0.
    Combines Redis-based passive discovery with P2P-direct active heartbeats.
    Ensures O(N) scaling while avoiding cloud-provider lock-in.
    """
    def __init__(self, node_id: str, secret: str, static_peers: List[Dict[str, Any]] = None, redis_client: Any = None):
        self.node_id = node_id
        self.secret = secret
        self.redis_client = redis_client
        self.peers = {p['node_id']: DCNPeer(**p) for p in (static_peers or [])}
        self.local_cache = {}
        self.raft_term = 0
        self.is_active = True
        self.region = os.getenv("DCN_REGION", "us-east")

    async def start_discovery_loop(self, interval: int = 30):
        """Main loop for broadcasting and receiving pulses."""
        logger.info(f"[DCN] Hybrid Gossip active for {self.node_id}")
        while self.is_active:
            try:
                await self.broadcast_heartbeat()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"[DCN] Discovery loop anomaly: {e}")
                await asyncio.sleep(10)

    async def broadcast_heartbeat(self):
        """Emits a heartbeat via Redis (Primary) or P2P (Fallback)."""
        pulse = {
            "node_id": self.node_id,
            "region": self.region,
            "timestamp": time.time(),
            "term": self.raft_term,
            "status": "ALIVE"
        }
        pulse["signature"] = self._sign_pulse(pulse)

        # 1. Attempt Redis Broadcast (Passive)
        if self.redis_client:
            try:
                await self.redis_client.publish("dcn:gossip:global", json.dumps(pulse))
                logger.debug(f"[DCN] Heartbeat broadcasted via Redis.")
                return
            except Exception as e:
                logger.warning(f"[DCN] Redis gossip failed, falling back to P2P: {e}")

        # 2. P2P Fallback (Active)
        # Select 3-5 random peers to avoid mesh explosion O(N^2)
        fanout = min(3, len(self.peers))
        if fanout == 0: return

        targets = random.sample(list(self.peers.values()), fanout)
        tasks = [self._send_direct_pulse(peer, pulse) for peer in targets]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_direct_pulse(self, peer: DCNPeer, pulse: Dict[str, Any]):
        """Transmits a pulse directly to a peer via HTTP/gRPC."""
        try:
            import grpc
            from backend.dcn import dcn_pb2, dcn_pb2_grpc
            
            if not dcn_pb2_grpc:
                raise ImportError("DCN Protos not available for P2P.")

            async with grpc.aio.insecure_channel(f"{peer.host}:{peer.port}") as channel:
                stub = dcn_pb2_grpc.DCNGossipServiceStub(channel)
                
                # Wrap pulse in request
                request = dcn_pb2.PulseRequest(
                    payload=json.dumps(pulse),
                    signature=pulse.get("signature", "")
                )
                
                # Unary call with 2s timeout
                response = await stub.PublishPulse(request, timeout=2.0)
                
                if response.success:
                    peer.last_heartbeat = pulse["timestamp"]
                    peer.status = "ALIVE"
                    logger.debug(f"[DCN] P2P pulse delivered to {peer.node_id}")
                else:
                    logger.warning(f"[DCN] P2P pulse rejected by {peer.node_id}: {response.message}")

        except Exception as e:
            peer.status = "UNREACHABLE"
            logger.debug(f"[DCN] P2P route to {peer.node_id} failed: {e}")

    def _sign_pulse(self, pulse: Dict[str, Any]) -> str:
        """HMAC-SHA256 signs the pulse metadata."""
        msg = f"{pulse['node_id']}:{pulse['timestamp']}:{pulse['term']}"
        return hmac.new(self.secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

    def verify_pulse(self, pulse: Dict[str, Any]) -> bool:
        """Verifies pulse authenticity."""
        msg = f"{pulse['node_id']}:{pulse['timestamp']}:{pulse['term']}"
        expected = hmac.new(self.secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(pulse.get("signature", ""), expected)

    async def get_active_peers(self) -> List[DCNPeer]:
        """Returns nodes seen in the last 60 seconds."""
        now = time.time()
        return [p for p in self.peers.values() if (now - p.last_heartbeat) < 60]

    def stop(self):
        self.is_active = False

import os
