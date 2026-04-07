import os
import json
import time
import hmac
import hashlib
import logging
import asyncio
import redis.asyncio as redis
from typing import Dict, Any, Optional, Callable

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
        # 🛡️ Graduation Audit: Graceful TLS/SSL Fallback for local/DCN clusters
        if r:
            self.r = r
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0") 
            is_ssl = redis_url.startswith("rediss://")
            
            # Sanitized kwargs to avoid 'unexpected keyword' errors on non-SSL connections
            kwargs = {"decode_responses": True}
            if is_ssl:
                kwargs["ssl"] = True
                kwargs["ssl_cert_reqs"] = None # Relaxing for DCN internal mesh
            else:
                kwargs["ssl"] = False
                
            self.r = redis.from_url(redis_url, **kwargs)
        self.node_id = NODE_ID
        self.secret = DCN_SECRET
        self.is_listening = False
        self.is_coordinator = False
        self.is_isolated = False
        self.current_term = 0
        self.fencing_token = None
        
        self.leader_key = "dcn:swarm:coordinator"
        self.term_key = "dcn:swarm:term"
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
            "send_ts": time.time(), # Added for RTT calculation
            "term": self.current_term, # Added for consensus
            "type": payload.get("type", "generic"),
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
            
            # --- Swarm Registry v2.2 (Dynamic Discovery) ---
            if pulse.get("type") == "node_heartbeat":
                node_data = pulse.get("payload", {})
                node_data["node_id"] = pulse.get("node")
                node_data["role"] = pulse.get("role")
                node_data["weight"] = pulse.get("weight")
                node_data["capabilities"] = node_data.get("capabilities", ["llm"])
                node_data["last_seen"] = time.time()
                
                # 🛠️ RTT Calculation: Sovereign Latency Compensation
                if pulse.get("send_ts"):
                    rtt = (time.time() - pulse["send_ts"]) * 1000 # ms
                    node_data["rtt_ms"] = round(rtt, 2)

                # 🛠️ Consensus: Update local term if peer has higher term
                peer_term = pulse.get("term", 0)
                if peer_term > self.current_term:
                    logger.info(f"[DCN] Term Update: Synchronizing Term {self.current_term} -> {peer_term}")
                    self.current_term = peer_term
                
                # Dynamic Discovery: Populate the shared hash registry
                await self.r.hset("dcn:swarm:nodes", pulse.get("node"), json.dumps(node_data))
                logger.debug(f"[DCN] Swarm Discovery: {pulse.get('node')} registered with {node_data['capabilities']} (RTT: {node_data.get('rtt_ms')}ms)")

            if asyncio.iscoroutinefunction(handler):
                await handler(pulse)
            else:
                handler(pulse)
                
        except json.JSONDecodeError:
            logger.error("[DCN] Failed to decode pulse JSON payload.")

    async def check_quorum(self) -> bool:
        """
        Hardened Quorum Check: N/2 + 1.
        Ensures the node is not isolated before accepting coordination.
        """
        try:
            nodes_raw = await self.r.hgetall("dcn:swarm:nodes")
            if not nodes_raw:
                return True # Standalone mode

            all_nodes = [json.loads(v) for v in nodes_raw.values()]
            now = time.time()
            
            # Count nodes seen in the last 60s
            active_nodes = [n for n in all_nodes if now - n.get("last_seen", 0) < 60]
            active_count = len(active_nodes)
            total_count = len(all_nodes)
            
            quorum_needed = (total_count // 2) + 1
            
            if active_count < quorum_needed:
                if not self.is_isolated:
                    logger.warning(f"⚠️ [DCN] QUORUM LOST: Node {self.node_id} is isolated ({active_count}/{quorum_needed} active). PAUSING coordination.")
                self.is_isolated = True
                return False
            
            if self.is_isolated:
                logger.info(f"✅ [DCN] QUORUM RESTORED: {active_count}/{quorum_needed} nodes active.")
            self.is_isolated = False
            return True
        except Exception as e:
            logger.error(f"[DCN] Quorum check failed: {e}")
            return False

    async def try_become_coordinator(self) -> bool:
        """
        Sovereign v13.2 Quorum-based Election.
        Uses Fencing Tokens and Term tracking to prevent split-brain.
        """
        # 1. Quorum Gate
        if not await self.check_quorum():
            self.is_coordinator = False
            return False

        try:
            # 2. Term & Token Resolution
            # If we are the coordinator, we refresh. If not, we try to claim.
            current_leader = await self.r.get(self.leader_key)
            
            if current_leader == self.node_id:
                # Refresh lease
                await self.r.expire(self.leader_key, self.lease_ttl)
                if not self.is_coordinator:
                    logger.info(f"👑 [DCN] Role Confirmed: {self.node_id} is COORDINATOR.")
                self.is_coordinator = True
                return True
            
            # If there's an active leader who isn't us, we back off
            if current_leader:
                self.is_coordinator = False
                return False

            # 3. Request Vote / Claim Leadership
            # Increment Term in Redis and claim leader key
            async with self.r.pipeline(transaction=True) as pipe:
                await pipe.incr(self.term_key)
                await pipe.get(self.term_key)
                res = await pipe.execute()
                
            new_term = int(res[1])
            self.current_term = new_term
            
            # Try to set leader key with EX and NX
            # Fencing Token = term:node_id:timestamp
            token = f"{new_term}:{self.node_id}:{int(time.time())}"
            
            success = await self.r.set(
                self.leader_key, 
                self.node_id, 
                nx=True, 
                ex=self.lease_ttl
            )
            
            if success:
                logger.info(f"🚀 [DCN] ELECTION WON: {self.node_id} promoted to Term {new_term}. Fencing Token: {token}")
                self.fencing_token = token
                await self.r.set(f"{self.leader_key}:token", token, ex=self.lease_ttl)
                self.is_coordinator = True
                return True
            
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
