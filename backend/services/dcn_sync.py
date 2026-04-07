import logging
import json
import asyncio
import hmac
import hashlib
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.redis_client import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

# Secret for fragment signing (Graduation Tier requirement)
DCN_SECRET = os.getenv("AUDIT_CHAIN_SECRET", "sovereign_monolith_genesis_v13").encode()

class CognitiveFragment(BaseModel):
    """
    Sovereign v13.1: DCN Fragment Schema.
    Represents a high-fidelity semantic unit for cross-instance sync.
    """
    fragment_id: str = Field(default_factory=lambda: os.urandom(8).hex())
    origin_instance: str = Field(default="monolith_prime")
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
    Sovereign DCN Protocol v13.1.0 Stable.
    Handles gossip propagation of high-fidelity cognitive fragments via Redis PubSub.
    """
    CHANNEL = "swarm:sync:v13"

    def __init__(self):
        self._sync_task: Optional[asyncio.Task] = None

    async def fragment_scrubber(self, fidelity: float) -> bool:
        """
        Sovereign v1.0.0-RC1: Fragment Scrubber.
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
            redis_client.publish(self.CHANNEL, fragment.json())

    async def start_listening(self):
        """Starts the background gossip listener."""
        if not HAS_REDIS: return
        self._sync_task = asyncio.create_task(self._listener_loop())
        logger.info("[DCN] Gossip engine listener active.")

    async def _listener_loop(self):
        pubsub = redis_client.pubsub()
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
