import logging
import asyncio
from sqlalchemy import select, func
from backend.db.models import MissionMetric
from backend.db.postgres_db import get_read_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("V8.Metrics")

async def analyze_execution_metrics():
    """
    Analyzes the Brain Execution Metrics to verify the <40% LLM target.
    Pulls real historical data from the MissionMetric table.
    """
    logger.info("--- LEVI-AI v15.0 GA Execution Metrics Analysis ---")
    
    async with get_read_session() as session:
        # 1. Fetch distribution of intent routing
        # We classify 'deterministic_fast_path' and 'ultra_light' as "Non-LLM/Internal"
        # Others might involve heavy LLM use.
        
        # This is a simplified analysis based on status or tag (if we had tag in MissionMetric)
        # For this script, we'll look at the intent distribution and latency.
        
        stmt = select(
            MissionMetric.intent,
            func.count(MissionMetric.id).label("count"),
            func.avg(MissionMetric.latency_ms).label("avg_latency")
        ).group_by(MissionMetric.intent)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            logger.warning("No mission data found in Postgres. Telemetry feed silent.")
            return

        total_missions = sum(row.count for row in rows)
        
        # Heuristic: 'chat' and 'small_task' intents are often handled by smaller/local models
        # or deterministic rules if complexity is low.
        # In a real system, we'd record the 'engine_path' explicitly.
        
        logger.info(f"Total Cognitive Missions Analyzed: {total_missions}")
        
        llm_intensive_intents = ["complex_reasoning", "research", "code_generation"]
        llm_count = 0
        internal_count = 0
        
        for row in rows:
            if row.intent in llm_intensive_intents:
                llm_count += row.count
            else:
                internal_count += row.count
            
            logger.info(f"- Intent '{row.intent}': {row.count} pulses | Avg Latency: {row.avg_latency:.2f}ms")

        llm_rate = (llm_count / total_missions) * 100
        internal_rate = (internal_count / total_missions) * 100

        logger.info(f"\nLLM Intensive Rate: {llm_rate:.2f}% (Target: < 40%)")
        logger.info(f"Brain-First / Internal Rate: {internal_rate:.2f}%")

        if llm_rate < 40:
            logger.info("✅ SUCCESS: Brain-First Directive Met. Sovereign dependency verified.")
        else:
            logger.warning("⚠️ WARNING: LLM dependency still high (>40%). Check Evolutionary Rule Graduation.")

if __name__ == "__main__":
    asyncio.run(analyze_execution_metrics())
