import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional

from backend.db.redis import HAS_REDIS_ASYNC, get_async_redis_client
from backend.models.events import SovereignEvent

logger = logging.getLogger(__name__)


class SovereignEventBus:
    """
    Redis Streams event bus with consumer-group helpers.
    Legacy callers can keep using ``emit`` / ``subscribe`` while newer foundation
    paths use ``emit_event`` / ``consume_batch`` / ``acknowledge_event``.
    """

    def __init__(self):
        self._async_client = None
        self._consumers: List[asyncio.Task] = []
        self.consumer_group = "levi-swarm"
        self.stream_prefix = "sovereign:stream"
        self.default_streams = [
            "missions.raw",
            "missions.waves",
            "missions.artifacts",
            "memory.events",
            "agent.results",
            "system.pulses",
            "mission_events",
            "mission_lifecycle",
            "system_pulses",
            "memory_events",
            "evolution_events",
            "kernel_events",
        ]

    async def _get_client(self):
        if self._async_client is None:
            self._async_client = get_async_redis_client()
        return self._async_client

    def _stream_key(self, topic: str) -> str:
        return f"{self.stream_prefix}:{topic}"

    async def ensure_groups(self, streams: Optional[Iterable[str]] = None, group: Optional[str] = None):
        client = await self._get_client()
        if not client or not HAS_REDIS_ASYNC:
            return

        group_name = group or self.consumer_group
        for topic in streams or self.default_streams:
            try:
                await client.xgroup_create(self._stream_key(topic), group_name, id="0", mkstream=True)
            except Exception:
                pass

    async def emit_event(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        mission_id: str,
        source: str,
        hmac_sig: str = "",
        validation_hash: Optional[str] = None,
    ) -> Optional[str]:
        event = {
            "event_type": event_type,
            "mission_id": mission_id,
            "payload": payload,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if hmac_sig:
            event["hmac_sig"] = hmac_sig
        if validation_hash:
            event["validation_hash"] = validation_hash
        return await self.emit(topic, event)

    async def emit(self, topic: str, data: Dict[str, Any]) -> Optional[str]:
        client = await self._get_client()
        if not client or not HAS_REDIS_ASYNC:
            logger.warning("[EventBus] Redis offline. Dropping event on %s", topic)
            return None

        try:
            event_model = SovereignEvent(**data)
            redis_payload = event_model.model_dump() if hasattr(event_model, "model_dump") else event_model.dict()
            redis_payload["payload"] = json.dumps(redis_payload["payload"])
            redis_payload["hmac_sig"] = str(data.get("hmac_sig", ""))
            event_id = await client.xadd(
                self._stream_key(topic),
                redis_payload,
                id="*",
                maxlen=100000,
                approximate=True,
            )
            logger.debug("[EventBus] Event emitted to %s: %s", topic, event_model.event_type)
            return event_id
        except Exception as exc:
            logger.error("[EventBus] Emission failure on %s: %s", topic, exc)
            raise

    async def consume_batch(
        self,
        consumer_id: str,
        topics: List[str],
        timeout_ms: int = 1000,
        count: int = 10,
        group: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        client = await self._get_client()
        if not client or not HAS_REDIS_ASYNC:
            return {}

        group_name = group or self.consumer_group
        await self.ensure_groups(topics, group_name)

        try:
            streams = {self._stream_key(topic): ">" for topic in topics}
            messages = await client.xreadgroup(
                group_name,
                consumer_id,
                streams,
                count=count,
                block=timeout_ms,
            )
        except Exception as exc:
            logger.error("[EventBus] Batch consumption failure: %s", exc)
            return {}

        result: Dict[str, List[Dict[str, Any]]] = {}
        for stream_key, events in messages or []:
            topic = stream_key.replace(f"{self.stream_prefix}:", "", 1)
            result[topic] = []
            for event_id, payload in events:
                event_data = payload.copy()
                if isinstance(event_data.get("payload"), str):
                    try:
                        event_data["payload"] = json.loads(event_data["payload"])
                    except json.JSONDecodeError:
                        logger.warning("[EventBus] Invalid JSON payload on %s/%s", topic, event_id)
                result[topic].append({"event_id": event_id, "data": event_data})
        return result

    async def acknowledge_event(self, topic: str, event_id: str, group: Optional[str] = None):
        client = await self._get_client()
        if not client or not HAS_REDIS_ASYNC:
            return
        try:
            await client.xack(self._stream_key(topic), group or self.consumer_group, event_id)
        except Exception as exc:
            logger.error("[EventBus] ACK failure on %s/%s: %s", topic, event_id, exc)

    async def get_pending(self, consumer_id: str, topic: str, group: Optional[str] = None) -> List[Dict[str, Any]]:
        client = await self._get_client()
        if not client or not HAS_REDIS_ASYNC:
            return []
        try:
            return await client.xpending_range(
                self._stream_key(topic),
                group or self.consumer_group,
                min="-",
                max="+",
                count=100,
                consumername=consumer_id,
            )
        except Exception as exc:
            logger.error("[EventBus] XPENDING failure on %s: %s", topic, exc)
            return []

    async def subscribe(self, topic: str, group: str, consumer_id: str, callback: Callable[[Dict[str, Any]], Any]):
        client = await self._get_client()
        if not client:
            return None

        stream_key = self._stream_key(topic)
        try:
            await client.xgroup_create(stream_key, group, id="0", mkstream=True)
        except Exception:
            pass

        async def _consumer_loop():
            logger.info("[EventBus] Consumer %s started for %s (group=%s)", consumer_id, topic, group)
            while True:
                try:
                    messages = await client.xreadgroup(group, consumer_id, {stream_key: ">"}, count=10, block=2000)
                    if not messages:
                        continue

                    for _, msg_list in messages:
                        for msg_id, payload in msg_list:
                            try:
                                event_data = payload.copy()
                                if isinstance(event_data.get("payload"), str):
                                    event_data["payload"] = json.loads(event_data["payload"])

                                if asyncio.iscoroutinefunction(callback):
                                    await callback(event_data)
                                else:
                                    callback(event_data)

                                await client.xack(stream_key, group, msg_id)
                            except Exception as cb_err:
                                logger.error("[EventBus] Callback error on %s [%s]: %s", topic, msg_id, cb_err)
                except Exception as loop_err:
                    logger.error("[EventBus] Consumer loop error for %s: %s", topic, loop_err)
                    await asyncio.sleep(2)

        task = asyncio.create_task(_consumer_loop())
        self._consumers.append(task)
        return task

    async def stop(self):
        for task in self._consumers:
            task.cancel()
        logger.info("[EventBus] All consumers shut down.")


sovereign_event_bus = SovereignEventBus()
