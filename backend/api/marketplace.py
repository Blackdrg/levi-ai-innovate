import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from backend.db.postgres_db import get_write_session, get_read_session
from backend.db.models import MarketplaceAgent, CustomAgent
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketplace", tags=["Sovereign Marketplace"])

@router.get("/browse")
async def browse_marketplace(
    category: str = Query(None),
    sort_by: str = Query("downloads") # downloads, rating, newest
):
    """
    Returns agents available in the global Sovereign Marketplace.
    """
    try:
        async with get_read_session() as session:
            query = select(MarketplaceAgent)
            
            if category:
                query = query.where(MarketplaceAgent.category == category)
                
            if sort_by == "rating":
                query = query.order_by(MarketplaceAgent.rating.desc())
            elif sort_by == "newest":
                query = query.order_by(MarketplaceAgent.created_at.desc())
            else:
                query = query.order_by(MarketplaceAgent.downloads.desc())
                
            res = await session.execute(query)
            return res.scalars().all()
    except Exception as e:
        logger.error(f"[Marketplace] Browse failure: {e}")
        return {"error": "The marketplace is closed for maintenance."}

@router.post("/publish/{agent_id}")
async def publish_to_marketplace(
    agent_id: str,
    price: int = Query(0),
    category: str = Query("General"),
    current_user: dict = Depends(get_current_user)
):
    """
    Publishes a custom agent to the global marketplace.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    
    try:
        async with get_read_session() as session:
            query = select(CustomAgent).where(CustomAgent.agent_id == agent_id, CustomAgent.user_id == user_id)
            res = await session.execute(query)
            agent = res.scalar_one_or_none()
            
            if not agent:
                raise HTTPException(status_code=404, detail="Agent pulse not found.")
            
        async with get_write_session() as session:
            # Check if already published
            existing_query = select(MarketplaceAgent).where(MarketplaceAgent.agent_id == agent_id)
            existing_res = await session.execute(existing_query)
            if existing_res.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Agent already manifests in the marketplace.")
            
            market_entry = MarketplaceAgent(
                agent_id=agent.agent_id,
                name=agent.name,
                creator_id=user_id,
                description=agent.description,
                price_units=price,
                category=category,
                config_json=agent.config_json
            )
            session.add(market_entry)
            
        return {"status": "success", "message": "Agent published to the Sovereign Marketplace."}
    except Exception as e:
        logger.error(f"[Marketplace] Publish failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to synchronize with marketplace.")

@router.post("/install/{market_id}")
async def install_agent(market_id: int, current_user: dict = Depends(get_current_user)):
    """
    Installs an agent from the marketplace to the user's private collection.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    
    try:
        async with get_read_session() as session:
            query = select(MarketplaceAgent).where(MarketplaceAgent.id == market_id)
            res = await session.execute(query)
            market_agent = res.scalar_one_or_none()
            
            if not market_agent:
                raise HTTPException(status_code=404, detail="Marketplace agent not found.")
                
        async with get_write_session() as session:
            # Clone to CustomAgent
            new_agent = CustomAgent(
                agent_id=f"installed_{market_agent.agent_id}_{uuid.uuid4().hex[:4]}",
                user_id=user_id,
                name=market_agent.name,
                description=f"Installed from Marketplace. Original creator: {market_agent.creator_id}",
                config_json=market_agent.config_json,
                is_public=0
            )
            session.add(new_agent)
            
            # Increment downloads count (if we had a direct reference, but we use the market_agent from read)
            # We'll do a quick update
            update_query = MarketplaceAgent.__table__.update().where(MarketplaceAgent.id == market_id).values(downloads=MarketplaceAgent.downloads + 1)
            await session.execute(update_query)
            
        return {"status": "success", "message": "Agent installed successfully."}
    except Exception as e:
        logger.error(f"[Marketplace] Install failure: {e}")
        raise HTTPException(status_code=500, detail="Agent installation failed.")
