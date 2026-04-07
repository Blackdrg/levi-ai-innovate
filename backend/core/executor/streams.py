import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

TASK_STREAM = "dcn:task_stream"
DLQ_STREAM = "dcn:task_stream:failed"
CONSUMER_GROUP = "dcn:orchestrators"
MAX_RETRIES = 3 # v2.1 Hardened limit

class StreamManager:
    """
    Sovereign Stream Manager v2.0.
    Orchestrates the Redis Streams lifecycle for distributed task execution.
    Features: Priority Queuing, Consumer Groups, and Auto-Claim logic.
    """

    def __init__(self):
        self.stream_name = TASK_STREAM
        self.group_name = CONSUMER_GROUP

    async def setup_groups(self):
        """Ensures the consumer group exists for stable task processing."""
        if not HAS_REDIS_ASYNC: return
        try:
            # Create stream if not exists, then create group
            await redis_client.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
            logger.info(f"[Streams] Consumer Group '{self.group_name}' initialized.")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("[Streams] Consumer Group already exists.")
            else:
                logger.error(f"[Streams] Group setup failure: {e}")

    async def enqueue_task(self, task_pkg: Dict[str, Any], priority: str = "medium") -> Optional[str]:
        """Pushes a task package into the stream with priority metadata."""
        if not HAS_REDIS_ASYNC: return None
        
        try:
            # Map priority to a numeric score if needed (Streams are FIFO, but we can use multiple streams or head-loading)
            # For v2, we use a single stream with a 'priority' field.
            msg_id = await redis_client.xadd(
                self.stream_name,
                {"payload": json.dumps(task_pkg), "priority": priority},
                maxlen=5000,
                approximate=True
            )
            return msg_id
        except Exception as e:
            logger.error(f"[Streams] Enqueue failure: {e}")
            return None

    async def pull_tasks(self, consumer_id: str, count: int = 1) -> List[Tuple[str, Dict[str, Any], int]]:
        """Reads new/pending tasks and returns (msg_id, payload, delivery_count)."""
        if not HAS_REDIS_ASYNC: return []
        
        try:
            # 1. Try pending first
            pending = await redis_client.xreadgroup(
                self.group_name, consumer_id, {self.stream_name: "0"}, count=count
            )
            
            # 2. Try fresh if no pending
            if not pending:
                fresh = await redis_client.xreadgroup(
                    self.group_name, consumer_id, {self.stream_name: ">"}, count=count, block=2000
                )
                if not fresh: return []
                entries = fresh[0][1]
            else:
                entries = pending[0][1]

            results = []
            for msg_id, data in entries:
                payload = json.loads(data["payload"])
                
                # Fetch delivery count (Audit Point: DLQ Safety)
                # Redis doesn't return delivery count in xreadgroup, we need xpending
                pending_info = await redis_client.xpending_range(self.stream_name, self.group_name, msg_id, msg_id, 1)
                deliv_count = pending_info[0]["times_delivered"] if pending_info else 1
                
                if deliv_count > MAX_RETRIES:
                    logger.warning(f"⚠️ [DLQ] Node-Red Alert: Task {msg_id} failed {deliv_count} times. Exiling to DLQ.")
                    await self.move_to_dead_letter(msg_id, payload, f"Max retries ({MAX_RETRIES}) exceeded.")
                    continue

                results.append((msg_id, payload, deliv_count))
            
            return results
        except Exception as e:
            logger.error(f"[Streams] Pull failure: {e}")
            return []

    async def move_to_dead_letter(self, msg_id: str, payload: Dict[str, Any], reason: str):
        """Exiles a poison pill task to the Dead Letter Stream for manual audit."""
        try:
            await redis_client.xadd(
                DLQ_STREAM,
                {"payload": json.dumps(payload), "failed_at": str(asyncio.get_event_loop().time()), "reason": reason},
                maxlen=1000
            )
            # Acknowledge it in the original stream to remove it
            await self.acknowledge_task(msg_id)
            logger.error(f"💀 [DLQ] Task EXILED: {payload.get('node_id')} (Reason: {reason})")
        except Exception as e:
            logger.error(f"[Streams] DLQ move failure: {e}")

    async def fail_task(self, msg_id: str, payload: Dict[str, Any]):
        """
        Handles a task failure via Tail-Retry (Deferred) logic.
        Re-enqueues at the tail to prevent immediate cascading failure loop.
        """
        try:
            # 1. ACK the old message
            await self.acknowledge_task(msg_id)
            
            # 2. Re-enqueue at the TAIL (FIFO) with a slight delay if needed (can be handled by worker sleep or just Redis FIFO)
            new_id = await self.enqueue_task(payload, priority="low") # Reduced priority for retries
            logger.info(f"🔄 [Streams] Tail-Retry triggered for {payload.get('node_id')}. New ID: {new_id}")
        except Exception as e:
            logger.error(f"[Streams] Fail-requeue failure: {e}")

    async def acknowledge_task(self, msg_id: str):
        """Marks a task as successfully processed."""
        if not HAS_REDIS_ASYNC: return
        try:
            await redis_client.xack(self.stream_name, self.group_name, msg_id)
        except Exception as e:
            logger.error(f"[Streams] Ack failure for {msg_id}: {e}")

    async def auto_claim_abandoned(self):
        """Claims tasks from dead consumers (idle > 60s)."""
        if not HAS_REDIS_ASYNC: return
        try:
            # XAUTOCLAIM returns (next_iterator, [claimed_msgs], [deleted_msgs])
            res = await redis_client.xautoclaim(
                self.stream_name, self.group_name, "orchestrator-recovery", 60000, start_id="0-0", count=10
            )
            if res[1]:
                logger.info(f"[Streams] Recovered {len(res[1])} abandoned tasks.")
        except Exception as e:
            logger.error(f"[Streams] Auto-claim failure: {e}")
