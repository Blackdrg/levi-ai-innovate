import asyncio
import logging
import os
from contextlib import suppress
from typing import Any, Dict, Optional

from backend.core.event_bus import event_bus
from backend.core.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class EventConsumer:
    """Pull events from Redis Streams and route them to durable handlers."""

    def __init__(self):
        self.memory_manager = MemoryManager()
        self._tasks: list[asyncio.Task] = []
        self._stop = asyncio.Event()

    async def start(self):
        await event_bus.ensure_groups(["memory.events", "agent.results", "system.pulses", "evolution.events", "kernel.events"])
        self._tasks = [
            asyncio.create_task(self.consume_memory_events(), name="event-consumer-memory"),
            asyncio.create_task(self.consume_agent_results(), name="event-consumer-agent-results"),
            asyncio.create_task(self.consume_pulses(), name="event-consumer-pulses"),
        ]

    async def stop(self):
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task

    async def consume_memory_events(self):
        consumer_id = f"mem-consumer-{os.getenv('NODE_ID', os.getenv('DCN_NODE_ID', 'alpha'))}"
        while not self._stop.is_set():
            try:
                events = await event_bus.consume_batch(
                    consumer_id=consumer_id,
                    topics=["memory.events"],
                    timeout_ms=5000,
                )
                for topic, event_list in events.items():
                    for event in event_list:
                        await self._handle_memory_event(event["data"])
                        await event_bus.acknowledge_event(topic, event["event_id"])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Memory consumer error: %s", exc)
                await asyncio.sleep(5)

    async def consume_agent_results(self):
        consumer_id = f"agent-consumer-{os.getenv('NODE_ID', os.getenv('DCN_NODE_ID', 'alpha'))}"
        while not self._stop.is_set():
            try:
                events = await event_bus.consume_batch(
                    consumer_id=consumer_id,
                    topics=["agent.results"],
                    timeout_ms=5000,
                )
                for topic, event_list in events.items():
                    for event in event_list:
                        await self._handle_agent_result(event["data"])
                        await event_bus.acknowledge_event(topic, event["event_id"])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Agent result consumer error: %s", exc)
                await asyncio.sleep(5)

    async def consume_pulses(self):
        consumer_id = f"pulse-consumer-{os.getenv('NODE_ID', 'alpha')}"
        while not self._stop.is_set():
            try:
                events = await event_bus.consume_batch(
                    consumer_id=consumer_id,
                    topics=["system.pulses", "evolution.events", "kernel.events"],
                    timeout_ms=5000,
                )
                for topic, event_list in events.items():
                    for event in event_list:
                        await self._handle_pulse_event(topic, event["data"])
                        await event_bus.acknowledge_event(topic, event["event_id"])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Pulse consumer error: %s", exc)
                await asyncio.sleep(5)

    async def _handle_memory_event(self, event_data: Dict[str, Any]):
        event_type = event_data.get("event_type")
        payload = event_data.get("payload", {})

        if event_type == "mission_completed":
            await self.memory_manager.store_mission(
                mission_id=payload["mission_id"],
                user_id=payload["user_id"],
                session_id=payload["session_id"],
                user_input=payload["user_input"],
                response=payload["response"],
                perception=payload.get("perception", {}),
                results=payload.get("results", []),
                fidelity=payload.get("fidelity"),
                policy=payload.get("policy"),
            )
        elif event_type == "fact_extracted":
            await self.memory_manager.index_fact_to_neo4j(
                payload.get("triplet", {}),
                user_id=payload.get("user_id"),
            )
        elif event_type == "MEMORY_HYGIENE":
            logger.info("🧹 [Hygiene] Starting memory resonance cycle...")
            from backend.core.memory.resonance_manager import get_resonance_manager
            rm = get_resonance_manager()
            await rm.trigger_all_cycles()

    async def _handle_pulse_event(self, topic: str, event_data: Dict[str, Any]):
        event_type = event_data.get("event_type")
        payload = event_data.get("payload", {})

        if event_type == "EVOLUTION_SWEEP":
            logger.info("🌱 [Evolution] Checking for training candidates...")
            try:
                from backend.services.evolution.engine import evolution_engine
                await evolution_engine.check_and_train()
            except Exception as e:
                logger.error(f"Evolution sweep failed: {e}")

        elif event_type == "PROCESS_HEALTH_CHECK":
            logger.info("🛡️ [Kernel] Running process health check...")
            from backend.kernel.kernel_wrapper import kernel
            await asyncio.to_thread(kernel.get_processes) 

        elif event_type == "SYSTEM_PULSE":
            logger.debug("💓 System Pulse Received.")
        elif event_type == "MEMORY_HYGIENE":
            logger.info("🧹 [Hygiene] Starting memory resonance cycle...")
            from backend.core.memory.resonance_manager import get_resonance_manager
            rm = get_resonance_manager()
            # This triggers a cycle for registered users (standalone or global)
            await rm.trigger_all_cycles()

    async def _handle_pulse_event(self, topic: str, event_data: Dict[str, Any]):
        event_type = event_data.get("event_type")
        payload = event_data.get("payload", {})

        if event_type == "EVOLUTION_SWEEP":
            logger.info("🌱 [Evolution] Checking for training candidates...")
            try:
                from backend.services.evolution.engine import evolution_engine
                await evolution_engine.check_and_train()
            except Exception as e:
                logger.error(f"Evolution sweep failed: {e}")

        elif event_type == "PROCESS_HEALTH_CHECK":
            logger.info("🛡️ [Kernel] Running process health check...")
            from backend.kernel.kernel_wrapper import kernel
            # The Microkernel's resource monitor loop (logic in lib.rs) already handles some of this,
            # but we can trigger additional user-space pruning here.
            await asyncio.to_thread(kernel.get_processes) 

        elif event_type == "SYSTEM_PULSE":
            logger.debug("💓 System Pulse Received.")

    async def _handle_agent_result(self, event_data: Dict[str, Any]):
        payload = event_data.get("payload", {})
        mission_id = payload.get("mission_id") or event_data.get("mission_id")
        result = payload.get("result")
        if not mission_id or result is None:
            return

        try:
            from backend.agents.critic_agent import CriticAgent, CriticInput

            critic = CriticAgent()
            audit = await critic._run(
                CriticInput(goal=mission_id, agent_output=str(result), context=payload)
            )
            if audit.get("success"):
                await event_bus.emit_event(
                    topic="missions.artifacts",
                    event_type="agent_result_validated",
                    payload={"mission_id": mission_id},
                    mission_id=mission_id,
                    source="event_consumer",
                )
        except Exception as exc:
            logger.error("Agent result handling failed: %s", exc)


event_consumer: Optional[EventConsumer] = None


async def start_event_consumers() -> EventConsumer:
    global event_consumer
    event_consumer = EventConsumer()
    await event_consumer.start()
    return event_consumer
