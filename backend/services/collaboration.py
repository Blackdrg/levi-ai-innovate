import logging
from typing import Dict, Any
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.api.v8.telemetry import broadcast_mission_event

logger = logging.getLogger(__name__)

class CollaborationService:
    """
    Sovereign Collaboration Hub (v13.0.0).
    Hybrid Model: Central Redis Hub for local sync + Pulse DCN for P2P.
    """
    
    @classmethod
    async def join_mission(cls, user_id: str, mission_id: str):
        """
        Adds a user to a shared mission session.
        """
        if not HAS_REDIS: return
        
        collab_key = f"collab:mission:{mission_id}:users"
        redis_client.sadd(collab_key, user_id)
        
        # Broadcast presence
        broadcast_mission_event(user_id, "collab_join", {
            "mission_id": mission_id,
            "user_id": user_id,
            "active_users": [u.decode() for u in redis_client.smembers(collab_key)]
        })
        
        logger.info(f"[Collab] User {user_id} joined mission {mission_id}")

    @classmethod
    async def sync_mission_state(cls, mission_id: str, state_update: Dict[str, Any], origin_user: str):
        """
        Broadcasts mission state changes to all collaborators.
        """
        if not HAS_REDIS: return
        
        collab_key = f"collab:mission:{mission_id}:users"
        collaborators = [u.decode() for u in redis_client.smembers(collab_key)]
        
        for user_id in collaborators:
            if user_id != origin_user:
                broadcast_mission_event(user_id, "collab_state_sync", {
                    "mission_id": mission_id,
                    "update": state_update,
                    "origin": origin_user
                })
        
        logger.debug(f"[Collab] Synced state for {mission_id} from {origin_user} to {len(collaborators)-1} peers.")

    @classmethod
    async def leave_mission(cls, user_id: str, mission_id: str):
        """
        Removes a user from a shared mission.
        """
        if not HAS_REDIS: return
        
        collab_key = f"collab:mission:{mission_id}:users"
        redis_client.srem(collab_key, user_id)
        
        broadcast_mission_event(user_id, "collab_leave", {
            "mission_id": mission_id,
            "user_id": user_id
        })
        
        logger.info(f"[Collab] User {user_id} left mission {mission_id}")
