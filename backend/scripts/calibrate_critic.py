import asyncio
import logging
from sqlalchemy import select, func, insert
from backend.db.postgres import PostgresDB
from backend.db.models import CriticCalibration, UserCalibration
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CalibrateCritic")

async def calibrate_all_users():
    """
    Sovereign v13.1 Phase 7: Bias Correction Engine.
    Analyzes historical critic divergence and calculates user-specific scoring offsets.
    """
    logger.info("🔧 Starting Weekly Critic Calibration...")
    
    async with PostgresDB._session_factory() as session:
        # 1. Fetch distinct user_ids from calibration ledger
        stmt = select(CriticCalibration.user_id).where(CriticCalibration.human_score != None).distinct()
        res = await session.execute(stmt)
        user_ids = [r[0] for r in res.all()]
        
        # Add 'global' for the fallback
        user_ids.append("global")
        
        for uid in user_ids:
            # 2. Calculate bias: average(human_score - primary_score)
            if uid == "global":
                bias_stmt = select(
                    func.avg(CriticCalibration.human_score - CriticCalibration.primary_score),
                    func.count(CriticCalibration.id)
                ).where(CriticCalibration.human_score != None)
            else:
                bias_stmt = select(
                    func.avg(CriticCalibration.human_score - CriticCalibration.primary_score),
                    func.count(CriticCalibration.id)
                ).where(CriticCalibration.user_id == uid, CriticCalibration.human_score != None)
                
            bias_res = await session.execute(bias_stmt)
            offset, count = bias_res.one()
            
            if offset is None:
                continue
                
            logger.info(f"[Calibrate] User: {uid} | Samples: {count} | Offset: {offset:+.4f}")
            
            # 3. Upsert into UserCalibration
            upsert_stmt = insert(UserCalibration).values(
                user_id=uid,
                bias_offset=float(offset),
                samples_analyzed=count,
                last_updated=datetime.now(timezone.utc)
            ).on_conflict_do_update(
                index_elements=['user_id'],
                set_={
                    'bias_offset': float(offset),
                    'samples_analyzed': count,
                    'last_updated': datetime.now(timezone.utc)
                }
            )
            await session.execute(upsert_stmt)
            
        await session.commit()
    logger.info("✅ Calibration complete. Scoring offsets synchronized.")

if __name__ == "__main__":
    asyncio.run(calibrate_all_users())
