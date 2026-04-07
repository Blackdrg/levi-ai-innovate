"""
Sovereign Swarm Sync Engine v13.0.0.
Distributed Cognitive Network (DCN) Bridge for Rule Synchronization.
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from backend.core.v8.rules_engine import RulesEngine
from backend.core.dcn.consistency import ConsistencyEngine
# Legacy Firestore Removed for v13.0.0 SQL Finality

logger = logging.getLogger(__name__)

class SovereignSync:
    """
    DCN Bridge Controller (v13.0.0).
    Synchronizes 'Crystallized Rules' across the LEVI Distributed Network via SQL.
    """
    
    SECRET_KEY = os.getenv("SWARM_SYNC_KEY", "sovereign_ensemble_2026").encode()

    @classmethod
    def _generate_signature(cls, data: str) -> str:
        return hmac.new(cls.SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()

    @classmethod
    def _verify_signature(cls, data: str, signature: str) -> bool:
        expected = cls._generate_signature(data)
        return hmac.compare_digest(expected, signature)

    @classmethod
    async def export_local_rules(cls) -> Dict[str, Any]:
        """Prepares a signed payload of local crystallized rules."""
        engine = RulesEngine()
        rules = engine.list_rules()
        
        payload_data = json.dumps({
            "swarm_id": os.getenv("SWARM_ID", "local_monolith"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rules": rules,
            "protocol_v": "13.0.0"
        })
        
        signature = cls._generate_signature(payload_data)
        
        return {
            "payload": payload_data,
            "signature": signature
        }

    @classmethod
    async def import_external_rules(cls, package: Dict[str, Any]) -> int:
        """Verifies and merges rules from an external swarm via v13 protocol."""
        payload = package.get("payload", "")
        signature = package.get("signature", "")
        
        if not payload or not signature:
            return 0
            
        if not cls._verify_signature(payload, signature):
            logger.error("[Sync-v13] Invalid signature detected. Rejecting foreign rules.")
            return 0
            
        try:
            data = json.loads(payload)
            foreign_rules = data.get("rules", {})
            engine = RulesEngine()
            
            count = 0
            for task, solution in foreign_rules.items():
                if task not in engine.rules.get("rules", {}):
                    engine.create_rule(task, solution)
                    count += 1
            
            if count > 0:
                logger.info(f"[Sync-v13] Successfully imported {count} rules from Swarm: {data.get('swarm_id')}")
                # Audit into SQL Fabric (Absolute Monolith v13)
                await cls._audit_sync(data.get("swarm_id"), count, "IMPORT")
                
                # Pulse: Notify Mobile Dashboard
                from backend.broadcast_utils import SovereignBroadcaster
                SovereignBroadcaster.broadcast({
                    "type": "NEURAL_SYNK_RECEIVED",
                    "swarm_id": data.get("swarm_id"),
                    "fragments": count
                })
            return count
        except Exception as e:
            logger.error(f"[Sync-v13] Anomaly during rule import: {e}")
            return 0

    @classmethod
    async def _audit_sync(cls, swarm_id: str, fragments: int, sync_type: str):
        """Persists DCN sync audit to Postgres SQL."""
        try:
            from backend.db.postgres_db import get_write_session
            from sqlalchemy import text
            async with get_write_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO dcn_sync_logs (swarm_id, sync_type, fragments_count, status)
                        VALUES (:sid, :type, :count, 'SUCCESS')
                    """),
                    {"sid": swarm_id, "type": sync_type, "count": fragments}
                )
        except Exception as e:
            logger.error(f"[Sync-v13] SQL Audit failure: {e}")

    @classmethod
    async def sync_with_collective_hub(cls):
        """
        Pushes local delta to the DCN Collective Hub (SQL Protocol).
        Broadcasts via Redis Pub/Sub for sub-second cluster sync.
        """
        logger.info("[Sync-v13] Initiating DCN Absolute Monolith Synchronization...")
        
        # 1. Local Redis Broadcast
        local_package = await cls.export_local_rules()
        from backend.db.redis import r as redis_client, HAS_REDIS
        if HAS_REDIS:
            try:
                redis_client.publish("sovereign:swarm_sync", json.dumps(local_package))
            except Exception as e:
                logger.warning(f"[Sync-v13] Local Broadcast Anomaly: {e}")

        # 3. Neural Audit (v13.2 Partition Handling)
        await cls.perform_neural_audit()
        
        logger.info(f"[Sync-v13] Neural Synchrony Pulse Complete. Exported {rules_count} fragments.")

    @classmethod
    async def perform_neural_audit(cls):
        """
        Cross-node Memory Validation (v13.2).
        Uses ConsistencyEngine to detect and resolve drift in mission state.
        """
        node_id = os.getenv("DCN_NODE_ID", "node-alpha")
        engine = ConsistencyEngine(node_id)
        
        logger.info(f"[Sync-v13] Initiating Neural Audit for node: {node_id}")
        await engine.reconcile()
        logger.debug("[Sync-v13] Neural Audit Complete.")
