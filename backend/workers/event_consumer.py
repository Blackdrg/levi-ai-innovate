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
        pulse_type = payload.get("pulse_type")

        # 1. EVOLUTION (PPO Optimization)
        if event_type == "EVOLUTION_SWEEP" or pulse_type == "EVOLUTION_SWEEP":
            logger.info("🌱 [Evolution] Checking for training candidates...")
            try:
                from backend.services.evolution.engine import evolution_engine
                await evolution_engine.check_and_train()
            except Exception as e:
                logger.error(f"Evolution sweep failed: {e}")

        # 2. KERNEL (Health & Processes)
        elif event_type == "PROCESS_HEALTH_CHECK" or pulse_type == "PROCESS_HEALTH_CHECK":
            logger.info("🛡️ [Kernel] Running process health check...")
            from backend.kernel.kernel_wrapper import kernel
            await asyncio.to_thread(kernel.get_processes) 

        # 3. MEMORY (Resonance & Hygiene)
        elif event_type == "MEMORY_HYGIENE" or pulse_type == "MEMORY_HYGIENE" or pulse_type == "EPISODIC_DRIFT_CHECK":
            logger.info(f"🧹 [Hygiene] Starting memory resonance cycle ({pulse_type or event_type})...")
            from backend.core.memory_manager import MemoryManager
            mm = MemoryManager()
            # If the specific method exists on mm, call it, otherwise trigger global resonance
            if hasattr(mm, 'cleanup_stale_working_memory'):
                await mm.cleanup_stale_working_memory()
            
            from backend.core.memory.resonance_manager import get_resonance_manager
            rm = get_resonance_manager()
            await rm.trigger_all_cycles()

        # 4. RECONCILIATION (System Self-Healing)
        elif pulse_type == "RECONCILIATION":
            logger.info("🛠️ [Reconciliation] Pulse: Running system-wide integrity checks.")
            from backend.workers.reconciliation_worker import reconciliation_worker
            asyncio.create_task(reconciliation_worker.run_full_reconciliation())

        # 5. AUTOMATION: Daily Tasks (Email summaries, etc)
        elif pulse_type == "DAILY_RESET":
            logger.info("📅 [Daily] Pulse: Triggering autonomous daily resets and summaries.")
            # Example: Trigger email summary mission for all active users
            from backend.core.orchestrator import _orchestrator
            # This would ideally fetch active users and spawn missions
            # For now, we log the intent as per Stage 6 Example
            logger.info("📧 [Automation] Summarizing emails and generating reports (Autonomous Intent).")

        # 6. STUDIO: Cleanup
        elif pulse_type == "STUDIO_CLEANUP":
            logger.info("🎨 [Studio] Pulse: Cleaning up temporary assets.")
            from backend.services.studio.utils import cleanup_temp_assets
            await cleanup_temp_assets()

        # 7. COMPLIANCE & SECURITY SWEEP
        elif pulse_type == "COMPLIANCE_SWEEP":
            logger.info("⚖️ [Compliance] Pulse: Starting autonomous security and HMAC audit sweep.")
            try:
                from backend.utils.audit_helper import SovereignAuditHelper
                asyncio.create_task(SovereignAuditHelper.verify_system_integrity())
            except Exception as e:
                logger.error(f"Compliance sweep failed: {e}")

        # 8. WEEKLY INTELLIGENCE CALIBRATION
        elif pulse_type == "WEEKLY_CALIBRATION":
            logger.info("🪐 [Evolution] Pulse: Weekly Intelligence Calibration (Shadow Audit Cycle).")
            from backend.core.evolution_engine import EvolutionaryIntelligenceEngine
            asyncio.create_task(EvolutionaryIntelligenceEngine.run_shadow_audit())

        elif event_type == "SYSTEM_PULSE" or pulse_type == "HEARTBEAT":
            logger.debug(f"💓 [Pulse] Topic: {topic} | Type: {pulse_type or event_type}")

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
