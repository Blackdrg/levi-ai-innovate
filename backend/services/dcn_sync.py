import logging
import json
import asyncio
import hmac
import hashlib
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.db.redis import get_redis_client as _get_sync_redis, HAS_REDIS

# Lazy accessor — resolved when actually used
def _redis():
    return _get_sync_redis()


logger = logging.getLogger(__name__)

# Secret for fragment signing (Graduation Tier requirement)
DCN_SECRET = os.getenv("AUDIT_CHAIN_SECRET", "sovereign_os_genesis_v14").encode()

class CognitiveFragment(BaseModel):
    """
    Sovereign v14.0: DCN Fragment Schema.
    Represents a high-fidelity semantic unit for cross-instance sync.
    """
    fragment_id: str = Field(default_factory=lambda: os.urandom(8).hex())
    origin_instance: str = Field(default="sovereign_alpha")
    payload: Dict[str, Any]
    fidelity_s: float = Field(ge=0.95) # Only High-Fidelity gossip allowed
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None

    def sign(self):
        """Signs the fragment with the instance secret."""
        msg = f"{self.fragment_id}:{self.fidelity_s}:{json.dumps(self.payload)}".encode()
        self.signature = hmac.new(DCN_SECRET, msg, hashlib.sha256).hexdigest()

    def verify(self) -> bool:
        """Verifies fragment integrity."""
        if not self.signature: return False
        msg = f"{self.fragment_id}:{self.fidelity_s}:{json.dumps(self.payload)}".encode()
        expected = hmac.new(DCN_SECRET, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)

class GossipEngine:
    """
    Sovereign DCN Protocol v14.0.0 Stable.
    Handles gossip propagation of high-fidelity cognitive fragments via Redis PubSub.
    """
    CHANNEL = "swarm:sync:v14"

    def __init__(self):
        self._sync_task: Optional[asyncio.Task] = None

    async def fragment_scrubber(self, fidelity: float) -> bool:
        """
        Sovereign v14.0.0-Autonomous-SOVEREIGN: Fragment Scrubber.
        Strictly gates inter-node sync to ensure only the highest fidelity data is gossiped.
        """
        SCRUB_THRESHOLD = 0.95 # Section 15.1 Requirement
        if fidelity >= SCRUB_THRESHOLD:
            return True
        logger.debug(f"[DCN] Fragment scrubbed: Fidelity {fidelity} < {SCRUB_THRESHOLD}")
        return False

    async def broadcast_fragment(self, payload: Dict[str, Any], fidelity: float):
        """Broadcasts a high-fidelity fragment to the swarm after scrubbing."""
        if not await self.fragment_scrubber(fidelity):
            return

        fragment = CognitiveFragment(payload=payload, fidelity_s=fidelity)
        fragment.sign()
        
        if HAS_REDIS:
            logger.info(f"[DCN] Gossiping high-fidelity fragment {fragment.fragment_id}")
            client = _redis()
            if client:
                client.publish(self.CHANNEL, fragment.json())

    async def start_listening(self):
        """Starts the background gossip listener."""
        if not HAS_REDIS: return
        from backend.utils.runtime_tasks import create_tracked_task
        self._sync_task = create_tracked_task(self._listener_loop(), name="dcn-gossip-listener")
        logger.info("[DCN] Gossip engine listener active.")

    async def _listener_loop(self):
        client = _redis()
        if not client:
            logger.warning("[DCN] No Redis client — gossip listener disabled.")
            return
        pubsub = client.pubsub()
        pubsub.subscribe(self.CHANNEL)
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    fragment = CognitiveFragment(**data)
                    # Audit Point 12: Verify HMAC signature before ingestion
                    if fragment.verify():
                        await self._ingest_fragment(fragment)
                    else:
                        logger.warning(f"[DCN] Tampered fragment detected: {fragment.fragment_id}")
                except Exception as e:
                    logger.error(f"[DCN] Gossip sync error: {e}")

    async def _ingest_fragment(self, fragment: CognitiveFragment):
        """Ingests a verified fragment into the local memory fabric (Level 2)."""
        logger.info(f"[DCN] Ingesting verified fragment {fragment.fragment_id} from {fragment.origin_instance}")
        # In RC1, ingestion involves adding to the FAISS 'global' index and Postgres Episodic ledger
        from backend.db.vector_store import SovereignVectorStore
        v_store = SovereignVectorStore()
        await v_store.add([fragment.payload.get("text", "")], [{"source": "gossip", "origin": fragment.origin_instance, "fidelity": fragment.fidelity_s}])
        pass

sovereign_swarm = GossipEngine()
