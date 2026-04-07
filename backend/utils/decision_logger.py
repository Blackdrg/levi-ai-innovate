import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC as HAS_REDIS

logger = logging.getLogger(__name__)

class DecisionLogger:
    """
    Sovereign Decision Logger v14.0.
    Ensures full traceability of Brain decisions and policies.
    """
    
    LOG_FILE = "logs/brain_decisions.jsonl"

    @staticmethod
    async def log_decision(request_id: str, query: str, scores: Dict[str, Any], policy: Dict[str, Any]):
        """
        Logs a brain decision to Redis and a JSON-L audit file.
        """
        trace = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "scores": scores,
            "policy": policy
        }
        
        # 1. Log to JSON-L file (Auditing)
        try:
            os.makedirs(os.path.dirname(DecisionLogger.LOG_FILE), exist_ok=True)
            with open(DecisionLogger.LOG_FILE, "a") as f:
                f.write(json.dumps(trace) + "\n")
        except Exception as e:
            logger.error(f"[DecisionLogger] Failed to write to audit log: {e}")

        # 2. Log to Redis (Real-time monitoring/Learning)
        if HAS_REDIS:
            try:
                await redis_client.setex(f"brain:trace:{request_id}", 86400, json.dumps(trace))
                # Push to a global trace list for processing
                await redis_client.lpush("brain:traces:recent", json.dumps(trace))
                await redis_client.ltrim("brain:traces:recent", 0, 999) # Keep last 1000
            except Exception as e:
                logger.error(f"[DecisionLogger] Failed to write to Redis: {e}")

        logger.info(f"[DecisionLogger] Trace logged for {request_id} Mode: {policy.get('mode')}")

decision_logger = DecisionLogger()
