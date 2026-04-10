"""
Sovereign Compensation Coordinator v14.1.0.
Manages deterministic rollbacks for failed complex cognitive missions.
"""

import logging
import asyncio
from typing import List, Dict, Any, Callable, Optional
from backend.core.orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

class CompensationCoordinator:
    """
    Orchestrates UNDO operations for mission-critical side effects.
    Supports registration of 'reversal' lambdas during DAG execution.
    """
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._stack: List[Dict[str, Any]] = []

    def register_step(self, node_id: str, forward_action: str, reversal_logic: Callable, params: Dict[str, Any]):
        """Registers a completed step and its corresponding reverse action."""
        self._stack.append({
            "node_id": node_id,
            "action": forward_action,
            "reverse": reversal_logic,
            "params": params
        })
        logger.debug(f"[Compensation] Registered reversal for {node_id} ({forward_action})")

    async def compensate(self) -> Dict[str, Any]:
        """
        Executes internal stack in REVERSE order (LIFO).
        Triggered when a Critical Path fails in GraphExecutor.
        """
        if not self._stack:
            return {"status": "noop", "steps": 0}

        logger.warning(f"[Compensation] STARTING ROLLBACK for mission {self.mission_id} ({len(self._stack)} steps)")
        results = []
        
        # Reverse the stack: LIFO
        for step in reversed(self._stack):
            node_id = step["node_id"]
            action = step["action"]
            reversal = step["reverse"]
            params = step["params"]
            
            try:
                logger.info(f"[Compensation] Reversing step {node_id}...")
                if asyncio.iscoroutinefunction(reversal):
                    await reversal(**params)
                else:
                    reversal(**params)
                results.append({"node_id": node_id, "status": "reversed"})
            except Exception as e:
                logger.error(f"[Compensation] FAILED to reverse {node_id}: {e}")
                results.append({"node_id": node_id, "status": "failed", "error": str(e)})

        return {
            "status": "completed",
            "mission_id": self.mission_id,
            "steps": results
        }

    @staticmethod
    def get_global_handlers() -> Dict[str, Callable]:
        """Returns standard reversal handlers for common actions."""
        return {
            "delete_file": lambda path: os.remove(path) if os.path.exists(path) else None,
            "rollback_transaction": lambda tx_id: logger.warning(f"Simulating DB Rollback for {tx_id}"),
            "cancel_order": lambda order_id: logger.warning(f"Simulating Order Cancellation for {order_id}")
        }
