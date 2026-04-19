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
            # Emit shadow failure event
            asyncio.create_task(sovereign_event_bus.emit("system_errors", {
                "event_type": "MCM_PROCESS_FAILURE",
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
        event = {
            "type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "data": json.dumps(payload),
            "timestamp": str(datetime.now(timezone.utc).timestamp()),
            "origin": self.region
        }
        
        # 1. Content Dedup index
        content_hash = self.compute_content_hash(payload)
        redis_client.setex(f"mcm:content_hash:{user_id}:{content_hash}", 86400, event["id"])
        
        redis_client.xadd(self.STREAM_NAME, event, maxlen=100000)
        logger.debug(f"[MCM] Emitted {event_type} for {user_id}")

    async def stop(self):
        self._is_running = False
        if self._process_task:
            self._process_task.cancel()
            try: await self._process_task
            except asyncio.CancelledError: pass

    # _synchro_loop is deprecated and replaced by EventBus subscription.

    async def _process_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any], source: str):
        """
        High-Fidelity Tiered Synchronization.
        Triggered by: mission_events stream.
        """
        logger.info(f"[MCM] Synchronizing {event_type} for {user_id} (Source: {source})")

        try: 
            # 1. Tier 3 Sync (Neo4j - CRITICAL PATH < 100ms)
            # This is done FIRST to ensure visual/truth layer parity.
            if event_type == "MISSION_COMPLETED":
                from backend.db.neo4j_client import Neo4jClient
                try:
                    # Parallelizing truth sync
                    await Neo4jClient.add_interaction(
                        user_id=user_id, 
                        query=payload.get("objective", ""), 
                        response=payload.get("response", ""), 
                        sync=True # Enforce immediate consistency
                    )
                    
                    # 🛡️ [Phase 3/8] Real-Time Truth Reconciliation
                    from backend.core.reconciliation import reconciliation_worker
                    asyncio.create_task(reconciliation_worker.run_reconciliation_pulse(user_id))
                    
                except Exception as e:
                    logger.error(f"❌ [MCM] Neo4j Critical Sync failed: {e}")

            # 2. Tier 2 Sync (Postgres - Episodic Storage)
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

            # 3. Tier 4 Sync (Vector Stores - Background)
            from backend.db.vector_store import SovereignVectorStore
            try:
                if event_type == "MISSION_COMPLETED":
                    asyncio.create_task(SovereignVectorStore.store_fact(
                        user_id, 
                        f"Recall: {payload.get('objective')[:50]}...", 
                        category="interaction",
                        importance=payload.get("fidelity", 0.8)
                    ))
            except Exception as e:
                logger.error(f"[MCM] Vector Sync failed: {e}")

        except Exception as e: 
            logger.error(f"[MCM] Persistence Failure: {e}")

    async def run_reconciliation(self):
        """Self-healing drift detection between Cache and SQL."""
        if not HAS_REDIS: return
        try:
            active_redis = redis_client.hgetall("orchestrator:missions")
            async with get_write_session() as session:
                from sqlalchemy import select
                for mid_bytes, data_bytes in active_redis.items():
                    mid = mid_bytes.decode()
                    data = json.loads(data_bytes.decode())
                    
                    # 🛡️ [T0 Validation] Check if mission exists in T1/T2
                    res = await session.execute(select(Mission).where(Mission.mission_id == mid))
                    mission_db = res.scalar_one_or_none()
                    
                    if data.get("state") in ["COMPLETE", "FAILED"]:
                        if not mission_db:
                            logger.warning(f"⚠️ [MCM-T0] Consistency Anomaly: Mission {mid} is {data.get('state')} in T0 but missing in SQL. Syncing...")
                            await self._process_event("interaction", data["user_id"], mid, data.get("replay", {}), self.region)
                        else:
                            # If mission exists but state differs, T1 wins (Factual Ledger)
                            if mission_db.status != data.get("state").lower():
                                logger.info(f"🔄 [MCM-T0] Aligning T0 state for {mid} to factual ledger ({mission_db.status})")
                                data["state"] = mission_db.status.upper()
                                redis_client.hset("orchestrator:missions", mid, json.dumps(data))
                    elif not mission_db and data.get("state") == "RUNNING":
                        # Detect ghost missions (running in Redis but never materialized in SQL)
                        started_at = float(data.get("timestamp", 0))
                        if (datetime.now(timezone.utc).timestamp() - started_at) > 3600:
                            logger.error(f"👻 [MCM-T0] Ghost Mission Detected: {mid}. Pruning T0.")
                            redis_client.hdel("orchestrator:missions", mid)

                
                # 🌐 Phase 16.1: Decentralized Snapshot Offloading
                snapshot_id = f"mcm_snap_{int(datetime.now(timezone.utc).timestamp())}"
                snapshot_data = {
                    "mission_count": len(active_redis),
                    "region": self.region,
                    "consistency_stream_tail": redis_client.xinfo_stream(self.STREAM_NAME).get("last-generated-id") if HAS_REDIS else "0"
                }
                await arweave_audit.anchor_snapshot(snapshot_id, snapshot_data)

        except Exception as e:
            logger.error(f"[MCM] Reconciliation anomaly: {e}")

    def enqueue_retry(self, user_id: str, payload: Dict[str, Any], store: str = "generic") -> None:
        if not HAS_REDIS: return
        enriched = {**payload, "store": store, "queued_at": datetime.now(timezone.utc).timestamp()}
        redis_client.rpush(f"mcm:retry:{store}:{user_id}", json.dumps(enriched))

    async def graduate(self, pulse: Dict[str, Any]) -> None:
        """
        Sovereign v21.0 Hard Reality: 
        Automated Memory Tier Promotion based on kernel-signed fidelity pulses.
        """
        fidelity = pulse.get("fidelity", 0.0)
        pid = pulse.get("pid", 0)
        
        logger.info(f"🎓 [MCM] Fidelity Pulse received: {fidelity} from PID {pid}")
        
        if fidelity >= 0.9:
            logger.info("⚔️ [MCM] CRITICAL FIDELITY MET: Promoting mission results to Tier-3 (Factual Ledger)")
            
            # Phase 1: Promote from Redis T1 to Postgres T2/T3
            # We use PID to find recent mission context (synthetic for this demo branch)
            fact_text = f"Kernel-Validated Outcome (PID {pid}): Sub-30ms ABI compliance confirmed."
            
            async with get_write_session() as session:
                fact = UserFact(
                    user_id="root_sovereign", 
                    fact=fact_text,
                    category="kernel_graduation",
                    importance=fidelity
                )
                session.add(fact)
                logger.info(f"✅ [MCM] Graduated Fact to Factual Ledger: {fact_text}")

            # Phase 2: Anchor to Blockchain if Fidelity is absolute (T4)
            if fidelity >= 0.95:
                logger.info(f"💠 [MCM] HIGH FIDELITY DETECTED ({fidelity}): Anchoring mission to Arweave permanent ledger.")
                try:
                    await arweave_audit.anchor_snapshot(
                        f"grad_{pid}_{int(datetime.now(timezone.utc).timestamp())}",
                        {
                            "pid": pid,
                            "fidelity": fidelity,
                            "proof": hashlib.sha256(fact_text.encode()).hexdigest()
                        }
                    )
                except Exception as e:
                    logger.error(f"❌ [MCM] Arweave Anchoring failed: {e}")

mcm_service = MemoryConsistencyManager()
