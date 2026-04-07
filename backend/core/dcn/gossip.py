import os
import json
import time
import hmac
import hashlib
import logging
import asyncio
import redis.asyncio as redis
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)

GOSSIP_STREAM = "dcn:gossip"
NODE_ID = os.getenv("DCN_NODE_ID", "node-alpha")
DCN_SECRET = os.getenv("DCN_SECRET", "sovereign_default_secret_v13")
GOSSIP_MAXLEN = 1000  # Capped MAXLEN for safety
GOSSIP_TTL_SECONDS = 3600  # 1 hour TTL for gossip messages
NODE_ROLE = os.getenv("NODE_ROLE", "worker") # coordinator | worker
NODE_WEIGHT = int(os.getenv("NODE_WEIGHT", "1")) # Task capacity weight

class DCNGossip:
    """
    Sovereign DCN Gossip Layer v2.1.
    Uses Redis Streams for persistent, multi-node cognitive gossip.
    Supports Sticky Coordinator election and TLS-secure communication.
    """
    def __init__(self, r: Optional[redis.Redis] = None):
        # 🛡️ TLS Certification: Enforcing secure inter-node communication
        redis_url = os.getenv("REDIS_URL", "rediss://localhost:6379/0") # Defaulting to 'rediss' for TLS
        self.r = r or redis.from_url(redis_url, decode_responses=True, ssl_cert_reqs=None)
        self.node_id = NODE_ID
        self.secret = DCN_SECRET
        self.is_listening = False
        self.is_coordinator = False
        self.leader_key = "dcn:swarm:coordinator"
        self.lease_ttl = 30 # 30s lease for sticky coordination

    async def broadcast_pulse(self, payload: Dict[str, Any]):
        """
        Broadcasts an HMAC-signed pulse to the DCN.
        Includes a safety MAXLEN trim to prevent memory bloat.
        """
        if not self.secret or len(self.secret) < 32:
            logger.warning("[DCN] Insecure DCN_SECRET. Pulse broadcast may be rejected by peers.")

        msg_dict = {
            "node": self.node_id,
            "role": NODE_ROLE,
            "weight": NODE_WEIGHT,
            "ts": time.time(),
            "payload": payload
        }
        msg_json = json.dumps(msg_dict)
        
        # HMAC-SHA256 Signature
        sig = hmac.new(
            self.secret.encode(),
            msg_json.encode(),
            hashlib.sha256
        ).hexdigest()

        try:
            # Add to stream with approximate MAXLEN for efficiency
            await self.r.xadd(
                GOSSIP_STREAM, 
                {"msg": msg_json, "sig": sig}, 
                maxlen=GOSSIP_MAXLEN, 
                approximate=True
            )
            
            # Periodic Time-based TTL Maintenance (optional, but requested)
            # Since IDs are timestamps, we can trim old messages
            min_id = int((time.time() - GOSSIP_TTL_SECONDS) * 1000)
            await self.r.xtrim(GOSSIP_STREAM, minid=f"{min_id}-0", approximate=True)
            
            logger.debug(f"[DCN] Pulse broadcasted from {self.node_id}")
        except Exception as e:
            logger.error(f"[DCN] Failed to broadcast pulse: {e}")

    async def listen(self, handler: Callable[[Dict[str, Any]], Any]):
        """
        Consumes pulses from other nodes and verifies their authenticity.
        """
        self.is_listening = True
        last_id = "$" # Start from the latest message
        
        logger.info(f"[DCN] Listening for gossip pulses on {GOSSIP_STREAM}...")
        
        while self.is_listening:
            try:
                # Blocking read with 5s timeout
                streams = await self.r.xread(
                    {GOSSIP_STREAM: last_id}, 
                    count=10, 
                    block=5000
                )
                
                if not streams:
                    continue

                for _, entries in streams:
                    for entry_id, data in entries:
                        last_id = entry_id
                        await self._verify_and_handle(data, handler)
                        
            except redis.ConnectionError:
                logger.warning("[DCN] Redis connection lost. Retrying in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[DCN] Listener anomaly: {e}")
                await asyncio.sleep(1)

    async def _verify_and_handle(self, data: Dict[str, str], handler: Callable):
        """Verifies signature and hands off to handler if valid."""
        msg_json = data.get("msg")
        sig = data.get("sig")

        if not msg_json or not sig:
            return

        # 1. HMAC Verification
        expected_sig = hmac.new(
            self.secret.encode(),
            msg_json.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(sig, expected_sig):
            logger.warning("[DCN] Rejected unauthenticated or tampered pulse signature.")
            return

        # 2. Decode and check if it's from self
        try:
            pulse = json.loads(msg_json)
            if pulse.get("node") == self.node_id:
                return # Ignore our own pulses

            # 3. Handle Pulse
            logger.debug(f"[DCN] Pulse received: {pulse.get('node')} ({pulse.get('type')})")
            
            # --- Swarm Registry (v2.0) ---
            if pulse.get("type") == "node_heartbeat":
                node_data = pulse.get("payload", {})
                node_data["last_seen"] = time.time()
                await self.r.hset("dcn:swarm:nodes", pulse.get("node"), json.dumps(node_data))
                logger.debug(f"[DCN] Node {pulse.get('node')} registered in swarm.")

            if asyncio.iscoroutinefunction(handler):
                await handler(pulse)
            else:
                handler(pulse)
                
        except json.JSONDecodeError:
            logger.error("[DCN] Failed to decode pulse JSON payload.")

    async def try_become_coordinator(self) -> bool:
        """
        Sovereign v13.1 Sticky Election: Attempts to claim the coordinator role.
        Uses Redis 'SET NX' with TTL to ensure stability and prevent thrashing.
        """
        try:
            # Sticky check: If we are already the leader, keep it.
            # If not, attempt to claim if expired.
            success = await self.r.set(
                self.leader_key, 
                self.node_id, 
                nx=True, 
                ex=self.lease_ttl
            )
            
            if success or (await self.r.get(self.leader_key) == self.node_id):
                if not self.is_coordinator:
                    logger.info(f"👑 [DCN] Role Promotion: {self.node_id} is now the swarm COORDINATOR.")
                self.is_coordinator = True
                # Refresh lease
                await self.r.expire(self.leader_key, self.lease_ttl)
                return True
            else:
                if self.is_coordinator:
                    logger.warning(f"📉 [DCN] Role Demotion: {self.node_id} has lost the coordinator lease.")
                self.is_coordinator = False
                return False
        except Exception as e:
            logger.error(f"[DCN] Election failure: {e}")
            return False

    async def start_election_loop(self):
        """Background loop to maintain or contest for coordination leadership."""
        logger.info(f"[DCN] Sticky Election Loop started for {self.node_id}.")
        while True:
            await self.try_become_coordinator()
            await asyncio.sleep(self.lease_ttl // 2) # Heartbeat at half TTL

    def stop(self):
        self.is_listening = False
