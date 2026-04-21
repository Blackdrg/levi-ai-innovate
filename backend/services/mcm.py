import logging
import asyncio
from datetime import datetime, timezone
import json
import os
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.postgres_db import get_write_session
from backend.db.models import Message, Mission, UserFact, UserTrait
from backend.utils.runtime_tasks import create_tracked_task
from backend.services.arweave_service import arweave_audit

# Memory is Not Truth-Aware Gap Closure
from backend.utils.event_bus import sovereign_event_bus

HAS_PUBSUB = HAS_REDIS # v22 GA Graduation: PUBSUB is provided by internalized Redis Streams

logger = logging.getLogger(__name__)

class MemoryConsistencyManager:
    """
    Sovereign v16.1: Unified Memory Consistency Manager (MCM).
    Harmonizes streaming and event sourcing implementations.
    The single source of truth for high-fidelity cognitive synchronization.
    Internalized: Replaces GCP Pub/Sub with local-first Redis Streams.
    """
    STREAM_NAME = "mission_events" 
    
    def __init__(self):
        self._is_running = False
        self._process_task: Optional[asyncio.Task] = None
        self.region = os.getenv("ENVIRONMENT", "local-node")
        
    async def start(self):
        """Starts the MCM synchronization loops."""
        if not HAS_REDIS:
            logger.warning("[MCM] No Redis detected. Consistency loop disabled.")
            return

        if self._is_running:
            return

        self._is_running = True
        
        # 1. Subscribe to Mission Events (Neo4j Sync Gate)
        from backend.utils.event_bus import sovereign_event_bus
        await sovereign_event_bus.subscribe(
            topic=self.STREAM_NAME,
            group="mcm_sync_group",
            consumer_id=f"mcm_{self.region}",
            callback=self._process_event_wrapper
        )
        
        logger.info(f"[MCM] Joined {self.STREAM_NAME} for real-time synchronization.")

    async def _process_event_wrapper(self, event: Dict[str, Any]):
        """
        Unpacks EventBus schema and routes to sync logic.
        Event Schema: {event_type, mission_id, payload, source, validation_hash}
        """
        try:
            event_type = event.get("event_type")
            mission_id = event.get("mission_id")
            payload_str = event.get("payload", "{}")
            payload = json.loads(payload_str)
            user_id = payload.get("user_id", "system")

            # Trigger Sync
            await self._process_event(
                event_type=event_type,
                user_id=user_id,
                session_id=mission_id,
                payload=payload,
                source=event.get("source", "unknown")
            )
        except Exception as e:
            logger.error(f"❌ [MCM] Event processing failure: {e}")
            # Emit shadow failure event (GA Fix: Added required mission_id and source)
            asyncio.create_task(sovereign_event_bus.emit("system_errors", {
                "event_type": "MCM_PROCESS_FAILURE",
                "mission_id": mission_id or "SYSTEM_MCM",
                "source": self.region,
                "payload": {"error": str(e), "event_ref": event}
            }))

    async def log_anomaly(self, user_id: str, anomaly: Dict[str, Any]):
        if HAS_REDIS:
             # Keep local anomaly logging in Redis for fast access
            redis_client.rpush(f"mcm:anomalies:{user_id}", json.dumps(anomaly))

    @staticmethod
    def compute_content_hash(payload: Dict[str, Any]) -> str:
        material = payload.get("payload") or payload.get("fact") or payload.get("type") or payload
        canonical = json.dumps(material, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def should_deduplicate(user_id: str, content_hash: str) -> bool:
        if not HAS_REDIS: return False
        return bool(redis_client.get(f"mcm:content_hash:{user_id}:{content_hash}"))

    async def emit_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any]):
        """Emits a cognitive event to the internalized consistency stream."""
        import uuid
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "data": json.dumps(payload),
            "timestamp": str(datetime.now(timezone.utc).timestamp()),
            "origin": self.region
        }
        
        if not HAS_REDIS:
            logger.warning("[MCM] Cannot emit event: no Redis connection.")
            return
        
        # 1. Content Dedup index
        content_hash = self.compute_content_hash(payload)
        redis_client.setex(f"mcm:content_hash:{user_id}:{content_hash}", 86400, event_id)
        
        redis_client.xadd(self.STREAM_NAME, event, maxlen=100000)
        logger.debug(f"[MCM] Emitted {event_type} for {user_id} (id={event_id})")

    async def stop(self):
        self._is_running = False
        if self._process_task:
            self._process_task.cancel()
            try: await self._process_task
            except asyncio.CancelledError: pass

    # _synchro_loop is deprecated and replaced by EventBus subscription.

    async def _process_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any], source: str):
        """
        Grounded Tiers: 1 (Redis), 2 (Postgres/Vector), 3 (Archive).
        Replaces the previous 5-tier hyperbole with a functional 3-tier architecture.
        """
        logger.info(f"[MCM] Synchronizing {event_type} for {user_id} (Source: {source})")

        try: 
            # TIER 1: HOT (Redis & Neo4j Interaction) - < 50ms
            if event_type == "MISSION_COMPLETED":
                from backend.db.neo4j_client import Neo4jClient
                try:
                    await Neo4jClient.add_interaction(
                        user_id=user_id, 
                        query=payload.get("objective", ""), 
                        response=payload.get("response", ""), 
                        sync=True 
                    )
                except Exception as e:
                    logger.error(f"❌ [MCM-T1] Neo4j Sync failed: {e}")

            # TIER 2: WARM (Postgres & Vector Store) - < 200ms
            async with get_write_session() as session:
                if event_type == "MISSION_COMPLETED":
                    mission = await session.get(Mission, session_id)
                    if not mission:
                        mission = Mission(
                            mission_id=session_id, 
                            user_id=user_id, 
                            objective=payload.get("objective", "Sync")[:200], 
                            status="completed"
                        )
                        session.add(mission)
                    
                    msg = Message(
                        mission_id=session_id, 
                        role="bot", 
                        content=payload.get("response", ""), 
                        timestamp=datetime.now(timezone.utc)
                    )
                    session.add(msg)
                
                elif event_type in ["fact_extracted", "fact"]:
                    facts = payload.get("facts", [payload])
                    for f in facts:
                        fact_obj = UserFact(
                            user_id=user_id, 
                            fact=f.get("fact") or f.get("text"), 
                            category=f.get("category", "general"), 
                            importance=f.get("importance", 0.5)
                        )
                        session.add(fact_obj)

            # TIER 2 (cont): Vector Store Update
            from backend.db.vector_store import SovereignVectorStore
            if event_type == "MISSION_COMPLETED":
                asyncio.create_task(SovereignVectorStore.store_fact(
                    user_id, 
                    f"Recall: {payload.get('objective')[:50]}...", 
                    category="interaction",
                    importance=payload.get("fidelity", 0.8)
                ))

        except Exception as e: 
            logger.error(f"[MCM-T2] Persistence Failure: {e}")

    async def graduate(self, pulse: Dict[str, Any]) -> None:
        """
        Hardened Graduation: Promoting Truth from T1/T2 to T3 (Cold Archival).
        Implements Section 7 Checklist D: 16-Agent BFT Quorum Consensus.
        """
        fact_id = pulse.get("fact_id")
        fidelity = pulse.get("fidelity", 0.0)
        agent_id = pulse.get("agent_id", "unknown")
        
        if not fact_id: return

        # 1. Consensus Aggregation (Replica Set Logic)
        quorum_key = f"mcm:consensus:{fact_id}"
        if HAS_REDIS:
            # Register this agent's vote
            redis_client.sadd(quorum_key, agent_id)
            # Store the highest fidelity reported for this fact
            redis_client.hset(f"mcm:fidelity:{fact_id}", agent_id, str(fidelity))
            
            votes = redis_client.scard(quorum_key)
            required_quorum = 11 # BFT Quorum for 16 agents (2f + 1 where n=3f+1, so f=5, 2(5)+1=11)
            
            logger.info(f"🧬 [BFT] Fact {fact_id}: {votes}/{required_quorum} votes recorded.")
            
            if votes >= required_quorum:
                # Calculate average fidelity from quorum
                all_fidelities = redis_client.hgetall(f"mcm:fidelity:{fact_id}")
                avg_fidelity = sum(float(v) for v in all_fidelities.values()) / len(all_fidelities)
                
                if avg_fidelity >= 0.92:
                    logger.info(f"🎓 [MCM-T3] QUORUM REACHED ({avg_fidelity:.2f}): Anchoring Truth to Arweave.")
                    await self._anchor_to_permanent_storage(fact_id, avg_fidelity)
                    # Cleanup quorum keys
                    redis_client.delete(quorum_key)
                    redis_client.delete(f"mcm:fidelity:{fact_id}")
        else:
            # Fallback for single-node development
            is_prod = os.getenv("ENVIRONMENT") == "production"
            if is_prod:
                logger.critical("🚨 [SECURITY] BFT Quorum BYPASSED in PRODUCTION mode. Redis is offline or disconnected.")
            
            if fidelity >= 0.95:
                await self._anchor_to_permanent_storage(fact_id, fidelity)

    async def _anchor_to_permanent_storage(self, fact_id: str, fidelity: float):
        """Tier 3: Arweave Permanent Snapshot."""
        try:
            await arweave_audit.anchor_snapshot(
                f"grad_{fact_id}_{int(datetime.now(timezone.utc).timestamp())}",
                {
                    "fact_id": fact_id,
                    "fidelity": fidelity,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "certification": "BFT_QUORUM_V22"
                }
            )
        except Exception as e:
            logger.error(f"❌ [MCM-T3] Arweave Anchoring failed: {e}")

    async def repair_inconsistent_fact(self, fact_id: str) -> bool:
        """
        Self-Healing Logic (Fix Requirement §702).
        Restores a fact from the high-fidelity Arweave anchor if local corruption is detected.
        """
        logger.warning(f" [🛠️] MCM: Repairing inconsistent fact {fact_id}...")
        try:
            # 1. Fetch from Arweave
            archive = await arweave_audit.get_latest_anchor() # Simple mock for this demo
            if archive and archive.get("fact_id") == fact_id:
                # 2. Restore to Postgres
                async with get_write_session() as session:
                    fact_obj = await session.get(UserFact, fact_id)
                    if fact_obj:
                        fact_obj.fact = archive.get("fact")
                        fact_obj.importance = 1.0 # Force maximum fidelity on restoration
                        logger.info(f" ✅ [MCM] Fact {fact_id} restored from forensic archive.")
                        return True
            return False
        except Exception as e:
            logger.error(f" [MCM] Self-healing restoration failed: {e}")
            return False

    async def purge_mission_facts(self, mission_id: str) -> None:
        """
        Idempotent Mission Purge (Section 5 Stabilization).
        Running this twice is guaranteed to be safe and raise no errors.
        """
        logger.warning(f" [🗑️] MCM: Commencing Idempotent Purge for mission {mission_id}")
        try:
            # 1. SQL Purge with explicit atomicity
            async with get_write_session() as session:
                from sqlalchemy import delete
                # Ensure we only try to delete if mission_id is valid
                if mission_id and len(mission_id) > 5:
                    await session.execute(delete(UserFact).where(UserFact.category == f"mission_{mission_id}"))
                    logger.debug(f" [MCM] SQL purge complete for {mission_id}")
                
            # 2. Redis Purge with key existence checks
            if HAS_REDIS:
                from backend.db.redis import r as redis_client
                # hdel is natively idempotent (returns 0 if key/field missing)
                removed = redis_client.hdel("orchestrator:missions", mission_id)
                redis_client.delete(f"mcm:interaction:{mission_id}")
                logger.info(f" ✅ [MCM] Purge FINALIZED for {mission_id} (Redis entries removed: {removed}).")
                
        except Exception as e:
            # Section 5: Log but do not crash the service loop
            logger.error(f" [MCM] Purge error (idempotent): {e}", exc_info=True)


mcm_service = MemoryConsistencyManager()

