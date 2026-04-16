import asyncio
import logging
from backend.utils.event_bus import sovereign_event_bus
from backend.models.events import SovereignEvent
from backend.core.memory_manager import MemoryManager
from backend.db.neo4j_connector import Neo4jStore
from backend.core.policy_gradient import policy_gradient
from backend.core.task_manager import task_manager
from backend.workers.reconciliation_worker import reconciliation_worker
from backend.tasks import monitor_embedding_drift

logger = logging.getLogger(__name__)

class SovereignEventWorker:
    """
    Sovereign Unified Event Worker v16.2.
    The 'heart' of the event-driven architecture.
    Subscribes to Redis Streams and triggers module-specific logic via UnifiedTaskManager.
    """
    
    def __init__(self):
        self.memory = MemoryManager()
        self.neo4j = Neo4jStore()

    async def start(self):
        logger.info("🚀 [SovereignWorker] Starting event-driven cognitive loops...")
        
        # 1. Mission Lifecycle Control
        await sovereign_event_bus.subscribe(
            topic="mission_events",
            group="cognitive_worker",
            consumer_id="worker_1",
            callback=self.handle_mission_completion
        )

        # 2. System Pulse Control (Autonomous Rhythm)
        await sovereign_event_bus.subscribe(
            topic="system_pulses",
            group="cognitive_worker",
            consumer_id="worker_1",
            callback=self.handle_system_pulse
        )

        logger.info("📡 [SovereignWorker] All streams subscribed. Standing by.")

    async def handle_mission_completion(self, event_data: dict):
        """
        Closed-Loop Intelligence: MISSION_COMPLETED -> Extraction -> Neo4j -> RL (PPO).
        """
        if event_data.get("event_type") != "MISSION_COMPLETED":
            return

        mission_id = event_data.get("mission_id")
        payload = event_data.get("payload", {})
        fidelity = payload.get("fidelity", 0.0)
        
        # 🛡️ HARD GATE: Evolution triggers ONLY on validated high-fidelity data
        if fidelity < 0.85:
            logger.warning(f"⚠️ [SovereignWorker] Fidelity too low ({fidelity:.2f}) for mission {mission_id}. Skipping evolution.")
            return

        # 1. Register extraction task
        task_id = await task_manager.register_task(
            module="Chronicler",
            action="ExtractAndSync",
            payload=payload,
            mission_id=mission_id
        )

        async def _sync_pipeline():
            # A. REAL-TIME NEO4J EXTRACTION (T4)
            logger.info(f"🌿 [SovereignWorker] Chronicler: Extracting knowledge for {mission_id}")
            from backend.agents.chronicler import ChroniclerAgent, ChroniclerInput
            chronicler = ChroniclerAgent()
            # Extract triplets using the LLM-backed chronicler agent
            extraction_res = await chronicler._run(ChroniclerInput(
                objective="Extract knowledge triplets",
                artifact=str(payload.get("response", ""))
            ))
            
            # B. PPO REWARD SIGNAL (RL Loop)
            # Reward is exactly the fidelity score from the critic
            from backend.core.policy_gradient import policy_gradient
            await policy_gradient.update_policy(mission_id, fidelity)
            
            return {"status": "synced", "extraction": extraction_res}

        await task_manager.execute_task(task_id, _sync_pipeline, mission_id=mission_id)

    async def handle_system_pulse(self, event_data: dict):
        """
        Responds to PulseEmitter to trigger self-healing (Reconciliation) and Evolution.
        """
        event_type = event_data.get("event_type")
        payload = event_data.get("payload", {})
        
        logger.info(f"💓 [SovereignWorker] Pulse Event: {event_type}")
        
        if event_type == "SYSTEM_PULSE":
            # REPAIR & MONITOR: Pulse emitted every 60s
            logger.info("🛠️ [SovereignWorker] Pulse: Running integrity and drift checks.")
            # 1. Reconciliation (T1, T2, T4 sync)
            asyncio.create_task(reconciliation_worker.run_full_reconciliation())
            # 2. Vector Drift Monitoring (FAISS)
            await monitor_embedding_drift("global")

        elif event_type == "EVOLUTION_SWEEP":
            # TRAINING: PPO Optimization pass (Every 10 mins via PulseEmitter)
            logger.info("🤖 [SovereignWorker] Pulse: Triggering Evolution (PPO Optimization Pass)...")
            from backend.core.policy_gradient import policy_gradient
            task_id = await task_manager.register_task(
                module="Evolution", 
                action="OptimizationPass", 
                payload=payload, 
                mission_id="evolution_scheduled"
            )
            await task_manager.execute_task(task_id, policy_gradient.run_optimization_pass)

        elif event_type == "MEMORY_HYGIENE":
            # CLEANUP: Maintenance (Every 20 mins via PulseEmitter)
            logger.info("🧹 [SovereignWorker] Pulse: Purging stale working memory.")
            from backend.core.memory_manager import MemoryManager
            mm = MemoryManager()
            await mm.cleanup_stale_working_memory()

if __name__ == "__main__":
    worker = SovereignEventWorker()
    asyncio.run(worker.start())
