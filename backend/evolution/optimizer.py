import logging
from typing import Dict, Any
from backend.core.policy_gradient import policy_gradient

logger = logging.getLogger(__name__)

class SystemOptimizer:
    """
    Sovereign System Optimizer (Engine 7).
    Coordinates system-wide parameter optimization.
    """
    
    async def optimize_all(self):
        """Triggers optimization across all applicable engines."""
        logger.info("⚙️ [SystemOptimizer] Initiating system-wide optimization pass...")
        
        # 1. RL-based Parameter Optimization (Engine 9)
        await policy_gradient.run_optimization_pass()
        
        # 2. Alignment Calibration (Engine 11)
        from backend.core.alignment import alignment_engine
        await alignment_engine.auto_calibrate()
        
        logger.info("✅ [SystemOptimizer] Optimization pass complete.")

optimizer = SystemOptimizer()
