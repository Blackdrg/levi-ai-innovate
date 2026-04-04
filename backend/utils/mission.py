import logging
from backend.redis_client import cache

logger = logging.getLogger(__name__)

class MissionControl:
    """
    Sovereign Mission Control v13.0.0.
    Handles mission-wide signals like cancellation and pausing.
    """
    
    @staticmethod
    def cancel_mission(mission_id: str):
        """Sets the cancellation flag for a specific mission."""
        logger.info(f"[MissionControl] Cancelling mission: {mission_id}")
        cache.set(f"cancel_mission:{mission_id}", "true", ex=3600)

    @staticmethod
    def is_cancelled(mission_id: str) -> bool:
        """Checks if a mission has been cancelled."""
        if not mission_id:
            return False
        val = cache.get(f"cancel_mission:{mission_id}")
        return val == "true"
