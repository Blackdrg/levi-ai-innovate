import logging
import os
from typing import Dict, Any, Optional
from backend.db.postgres import PostgresDB
from backend.db.models import UserCredit
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

class BillingService:
    """
    Sovereign v14.1 Billing & Monetization Service.
    Manages user cognitive credits and subscription tiers.
    """
    
    TIER_LIMITS = {
        "seeker": 100.0,   # Monthly free credits
        "pro": 1000.0,     # Pro tier
        "creator": 5000.0  # Creator/Enterprise tier
    }

    async def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        """Retrieves credit status for a user."""
        async with PostgresDB._session_factory() as session:
            stmt = select(UserCredit).where(UserCredit.user_id == user_id)
            res = await session.execute(stmt)
            credits = res.scalar_one_or_none()
            
            if not credits:
                # Initialize seeker credits
                credits = UserCredit(user_id=user_id)
                session.add(credits)
                await session.commit()
            
            return {
                "user_id": user_id,
                "credits": credits.credits_remaining,
                "tier": credits.tier
            }

    async def deduct_credits(self, user_id: str, amount: float) -> bool:
        """Deducts credits for a mission. Returns False if insufficient."""
        async with PostgresDB._session_factory() as session:
            stmt = select(UserCredit).where(UserCredit.user_id == user_id)
            res = await session.execute(stmt)
            credits = res.scalar_one_or_none()
            
            if not credits or credits.credits_remaining < amount:
                logger.warning(f"[Billing] Insufficient credits for {user_id} ({amount} requested).")
                return False
            
            credits.credits_remaining -= amount
            await session.commit()
            return True

    async def add_credits(self, user_id: str, amount: float):
        """v14.1 Refund/Credit logic."""
        async with PostgresDB._session_factory() as session:
            stmt = update(UserCredit).where(UserCredit.user_id == user_id).values(
                credits_remaining=UserCredit.credits_remaining + amount
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"[Billing] Credited {amount} back to {user_id}.")

    async def upgrade_tier(self, user_id: str, new_tier: str):
        """Upgrades a user to a higher sovereign tier."""
        async with PostgresDB._session_factory() as session:
            stmt = update(UserCredit).where(UserCredit.user_id == user_id).values(
                tier=new_tier,
                credits_remaining=self.TIER_LIMITS.get(new_tier, 100.0)
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"[Billing] User {user_id} upgraded to {new_tier}.")

# Global instance
billing_service = BillingService()
