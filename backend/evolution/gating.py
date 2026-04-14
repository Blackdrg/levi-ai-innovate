import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SafetyGating:
    """
    Sovereign Evolution Safety Gating (v16.0).
    Enforces strict quality and safety thresholds before graduating autonomous rules.
    """
    REQUIRED_SAMPLES = 500
    MIN_SUCCESS_RATE = 0.95

    async def validate_rule(self, rule_id: str) -> bool:
        """
        Validate a proposed rule against safety thresholds.
        Action: Safety Gating.
        """
        from backend.db.redis import r as redis
        if not redis: return False
        
        rule_data = await redis.get(f"evolution:pending_rules:{rule_id}")
        if not rule_data:
            logger.warning(f"[Gating] Rule {rule_id} not found.")
            return False
            
        rule = json.loads(rule_data)
        samples = rule.get("sample_count", 0)
        success_rate = rule.get("avg_success_rate", 0.0)
        
        # Enforce Gating
        is_valid = (samples >= self.REQUIRED_SAMPLES and success_rate >= self.MIN_SUCCESS_RATE)
        
        if is_valid:
            logger.info(f"✅ [Gating] Rule {rule_id} PASSED safety gates ({samples} samples, {success_rate:.2f} success).")
        else:
            logger.warning(f"❌ [Gating] Rule {rule_id} REJECTED. Samples: {samples}/{self.REQUIRED_SAMPLES}, Rate: {success_rate:.2f}/{self.MIN_SUCCESS_RATE}")
            
        return is_valid
