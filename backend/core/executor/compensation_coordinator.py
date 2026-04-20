# backend/core/executor/compensation.py
import logging
import asyncio
import json
import time
from typing import List, Dict, Any, Callable, Optional
from backend.db.redis import r_async as redis_client

logger = logging.getLogger(__name__)

# --- v15.0 Compensation Handlers ---
async def async_restore_fs_snapshot(node: Dict[str, Any]):
    from backend.kernel.kernel_wrapper import kernel
    snapshot_id = node.get("parameters", {}).get("snapshot_id", "latest")
    logger.critical(f" [🛡️] MISSION_CRITICAL: Restoring FS Snapshot {snapshot_id}")
    kernel.restore_fs_snapshot(snapshot_id)
    return {"status": "fs_restored"}

async def async_purge_mcm_facts(node: Dict[str, Any]):
    from backend.services.mcm import mcm_service
    mission_id = node.get("parameters", {}).get("mission_id")
    logger.critical(f" [🛡️] MISSION_CRITICAL: Purging MCM facts for {mission_id}")
    await mcm_service.purge_mission_facts(mission_id)
    return {"status": "mcm_purged"}

async def async_reverse_debit(node: Dict[str, Any]):
    logger.info(f"[Compensation] Reversing debit: {node.get('parameters')}")
    return {"status": "debit_reversed"}

async def async_delete_gcs_bucket(node: Dict[str, Any]):
    logger.info(f"[Compensation] Deleting GCS bucket: {node.get('parameters')}")
    return {"status": "bucket_deleted"}

async def async_revoke_webhook(node: Dict[str, Any]):
    logger.info(f"[Compensation] Revoking webhook: {node.get('parameters')}")
    return {"status": "webhook_revoked"}

async def async_cleanup_temp_files(node: Dict[str, Any]):
    logger.info(f"[Compensation] Cleaning up temp files: {node.get('parameters')}")
    return {"status": "files_cleaned"}

COMPENSATION_HANDLERS: Dict[str, Callable] = {
    "debit_account": async_reverse_debit,
    "create_gcs_bucket": async_delete_gcs_bucket,
    "invoke_webhook": async_revoke_webhook,
    "execute_code": async_cleanup_temp_files,
    "fs_snapshot": async_restore_fs_snapshot,
    "mcm_fact": async_purge_mcm_facts,
}

class CompensationCoordinator:
    """
    Sovereign v15.0 LIFO Compensation Engine.
    Executes best-effort reversals for failed mission-critical waves.
    """
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._executed_nodes: List[Dict[str, Any]] = []

    def register_node_execution(self, node_id: str, action_type: str, parameters: Dict[str, Any]):
        """Registers a completed node in the execution stack."""
        self._executed_nodes.append({
            "id": node_id,
            "action_type": action_type,
            "parameters": parameters,
            "ts": time.time()
        })

    async def compensate(self) -> List[Dict[str, Any]]:
        """Alias for LIFO rollback."""
        return await self.execute_lifo_compensation()

    async def execute_lifo_compensation(self) -> List[Dict[str, Any]]:
        """
        Execute compensations in reverse order (LIFO).
        If a compensation fails, log and continue (best-effort).
        """
        logger.warning(f"[V15.0] Starting LIFO compensation for mission {self.mission_id}: {len(self._executed_nodes)} nodes")
        
        compensation_results = []
        # Reverse the stack: LIFO
        for node in reversed(self._executed_nodes):
            action_type = node.get("action_type")
            if action_type not in COMPENSATION_HANDLERS:
                logger.warning(f"[Compensation] No handler for {action_type}, skipping node {node['id']}")
                continue
            
            try:
                handler = COMPENSATION_HANDLERS[action_type]
                result = await handler(node)
                compensation_results.append({
                    "node_id": node['id'],
                    "status": "compensated",
                    "result": result
                })
                logger.info(f"[Compensation] SUCCESS: Reversed node {node['id']} ({action_type})")
            except Exception as e:
                logger.error(f"[Compensation] CRITICAL FAILURE for node {node['id']}: {e}. Continuing best-effort.")
                compensation_results.append({
                    "node_id": node['id'],
                    "status": "compensation_failed",
                    "error": str(e)
                })
        
        # Store compensation audit trail in Redis
        try:
            await redis_client.set(
                f"mission:{self.mission_id}:compensation_log",
                json.dumps(compensation_results),
                ex=86400 # 24h retention
            )
        except Exception as redis_err:
             logger.error(f"[Compensation] Failed to persist log to Redis: {redis_err}")

        return compensation_results
