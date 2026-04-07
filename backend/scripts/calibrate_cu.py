import asyncio
import logging
from sqlalchemy import select
from backend.db.postgres import PostgresDB
from backend.db.models import BenchmarkLedger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("calibration")

async def calibrate():
    """
    Analyzes BenchmarkLedger and recommends the new CU threshold.
    """
    logger.info("🛡️ Initiating CU Calibration Protocol...")
    
    try:
        async with PostgresDB._session_factory() as session:
            # Query for the latest p95 latency for the L3 tier (70B)
            stmt = select(BenchmarkLedger).where(BenchmarkLedger.tier == "L3").order_by(BenchmarkLedger.created_at.desc()).limit(4)
            result = await session.execute(stmt)
            benchmarks = result.scalars().all()
            
            if not benchmarks:
                logger.warning("⚠️ No benchmark data found. Run 'python backend/scripts/benchmark_models.py' first.")
                return

            # Analyze p95 at various context lengths
            max_p95 = max(b.p95_latency_ms for b in benchmarks)
            
            # Recalibrate Threshold:
            # Current CU Abort Threshold is 200 (Arbitrary).
            # We want a threshold that reflects real-world L3 execution.
            # Assume 1 CU = 100ms of reasoning time as a baseline.
            new_threshold = int(max_p95 / 100) * 10
            
            # Clamp between 100 and 1000
            final_threshold = max(100, min(1000, new_threshold))
            
            logger.info("📊 Calibration Results (Tier L3):")
            logger.info(f"  Max p95 Latency: {max_p95:.2f}ms")
            logger.info(f"  Recommended CU Abort Threshold: {final_threshold} CU")
            logger.info("  (Current Threshold: 200 CU)")

            # Provide the update command
            print("\n" + "="*40)
            print("🚀 UPDATED SYSTEM PROTOCOL REQUIRED")
            print("Action: Update backend/config/system.py")
            print(f"Set: CU_ABORT_THRESHOLD = {final_threshold}")
            print("="*40 + "\n")
            
    except Exception as e:
        logger.error(f"❌ Calibration failed: {e}")
    finally:
        await PostgresDB.close()

if __name__ == "__main__":
    asyncio.run(calibrate())
