import logging
import asyncio
from datetime import datetime, timezone
from backend.celery_app import celery_app
from backend.api.telemetry import broadcast_mission_event
from backend.core.learning_loop import LearningLoop

logger = logging.getLogger(__name__)

@celery_app.task(name="backend.services.orchestrator.learning_tasks.run_autonomous_evolution")
def run_autonomous_evolution():
    """
    Sovereign v15.0-GA: Daily Learning Cycle.
    Analyzes execution traces to distill optimal agent sequences and patterns.
    """
    from backend.utils.concurrency import CircuitBreaker
    if CircuitBreaker.is_open():
        logger.warning("[Evolver] Circuit Breaker OPEN. Skipping autonomous analysis.")
        return

    async def _run():
        logger.info("[Evolver] Starting daily trace analysis and rule graduation...")
        
        # 1. Trigger Feedback Engine Analysis
        await LearningLoop.analyze_traces()
        
        # 2. Trigger Rule Engine Graduation 
        # (analyze_traces already calls distill_graduated_rules internally)
        
        # 3. Trigger Evolutionary Dreaming (Engine 7)
        from backend.core.evolution_engine import EvolutionaryIntelligenceEngine
        await EvolutionaryIntelligenceEngine.run_dreaming_session()
        
        # 4. Trigger Self-Healing Analysis (Phase 3.5)
        await EvolutionaryIntelligenceEngine.analyze_system_fragility()

        # 5. Trigger Policy Gradient RL Optimization (Phase 3.6)
        from backend.core.policy_gradient import policy_gradient
        await policy_gradient.run_optimization_pass()

        # 4. Telemetry Update
        broadcast_mission_event("system", "evolution_complete", {
            "message": "Daily learning cycle complete. Swarm algorithms optimized.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info("[Evolver] Full learning cycle complete.")

    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(_run())
    else:
        loop.run_until_complete(_run())

@celery_app.task(name="backend.services.orchestrator.learning_tasks.prune_expired_data")
def prune_expired_data():
    """
    Data Lifecycle Management: Removes stale documents and logs.
    """
    import os
    import time
    from pathlib import Path

    UPLOAD_DIR = Path("backend/data/uploads")
    if not UPLOAD_DIR.exists():
        return

    now = time.time()
    count = 0
    # Prune files older than 30 days
    for file_path in UPLOAD_DIR.glob("*"):
        if os.path.isfile(file_path):
            if now - os.path.getmtime(file_path) > (30 * 86400):
                os.remove(file_path)
                count += 1
    
    logger.info(f"[Maintenance] Pruned {count} expired files.")

@celery_app.task(name="backend.services.orchestrator.learning_tasks.unbound_training_cycle")
def unbound_training_cycle():
    """
    Sovereign v15.0-GA: Unbound Wisdom Capture.
    Captures weekly high-fidelity data and triggers autonomous fine-tuning (LoRA).
    """
    async def _run():
        logger.info("[Unbound] Exporting weekly high-fidelity corpus...")
        await LearningLoop.export_for_finetuning("backend/data/weekly_corpus.jsonl", limit=1000)
        
        # --- Phase 3.8: Autonomous LoRA fine-tuning ---
        from backend.services.evolution.lora_trainer import lora_trainer
        await lora_trainer.run_maintenance_cycle()
        
    asyncio.run(_run())


@celery_app.task(name="backend.services.orchestrator.learning_tasks.run_shadow_audit_task")
def run_shadow_audit_task():
    """
    Phase 3.2: Automated Shadow Audit Loop.
    Validates graduated rules against deep LLMs to detect cognitive drift.
    """
    from backend.core.evolution_engine import EvolutionaryIntelligenceEngine
    
    async def _run():
        logger.info("[ShadowAudit] Starting periodic validation of graduated rules...")
        await EvolutionaryIntelligenceEngine.run_shadow_audit()
        logger.info("[ShadowAudit] Shadow audit cycle complete.")

    asyncio.run(_run())

@celery_app.task(name="backend.services.orchestrator.learning_tasks.crystallize_patterns_task")
def crystallize_patterns_task():
    """
    Phase 3.3: Autonomous Pattern Crystallization.
    Transforms high-fidelity mission results into hard-coded fast-path rules.
    """
    from backend.core.evolution_engine import EvolutionaryIntelligenceEngine

    async def _run():
        logger.info("[Evolution] Awakening the Dreaming Loop for pattern crystallization...")
        await EvolutionaryIntelligenceEngine.run_dreaming_session()
        logger.info("[Evolution] Crystallization dreaming complete.")

    asyncio.run(_run())
