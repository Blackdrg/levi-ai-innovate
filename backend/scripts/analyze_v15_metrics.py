import logging
import asyncio
from sqlalchemy import select, func
from backend.db.models import MissionMetric
from backend.db.postgres_db import get_read_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("V15.Metrics")

async def analyze_execution_metrics():
    """
    Analyzes the Sovereign OS v15.0 GA Execution Metrics.
    Verifies the <40% LLM directive and engine distribution.
    """
    logger.info("--- LEVI-AI v15.0 GA Execution Metrics Analysis ---")
    
    async with get_read_session() as session:
        # Fetch distribution of intent routing
        stmt = select(
            MissionMetric.intent,
            func.count(MissionMetric.id).label("count"),
            func.avg(MissionMetric.latency_ms).label("avg_latency"),
            func.avg(MissionMetric.accuracy_score).label("avg_accuracy")
        ).group_by(MissionMetric.intent)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            logger.warning("No mission data found in Postgres. Telemetry feed silent.")
            return

        total_missions = sum(row.count for row in rows)
        logger.info(f"Total Cognitive Missions Analyzed: {total_missions}")
        
        # Rule Graduation Heuristic
        # v15.0 GA uses GraduatedRules for 'deterministic' paths.
        # We track if missions were served by the Fast-Path.
        
        llm_intensive_intents = ["complex_reasoning", "research", "code_generation"]
        llm_count = 0
        internal_count = 0
        
        for row in rows:
            if row.intent in llm_intensive_intents:
                llm_count += row.count
            else:
                internal_count += row.count
            
            logger.info(f"- Intent '{row.intent}': {row.count} pulses | Latency: {row.avg_latency:.2f}ms | Fidelity: {row.avg_accuracy:.2f}")

        llm_rate = (llm_count / total_missions) * 100
        internal_rate = (internal_count / total_missions) * 100

        logger.info(f"\nLLM Intensive Rate: {llm_rate:.2f}% (Target: < 40%)")
        logger.info(f"Sovereign Cache/Rule Rate: {internal_rate:.2f}%")

        if llm_rate < 40:
            logger.info("✅ SUCCESS: Brain-First Directive Met. Sovereign dependency verified.")
        else:
            logger.warning("⚠️ WARNING: LLM dependency high (>40%). Potential Rule Graduation bottleneck.")

if __name__ == "__main__":
    asyncio.run(analyze_execution_metrics())
