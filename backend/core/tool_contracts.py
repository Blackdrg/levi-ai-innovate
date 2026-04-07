"""
backend/services/orchestrator/tool_contracts.py

Standardized contracts for all LEVI AI tools and agents.
Every agent in agent_registry.py must adhere to these models.
"""
from typing import Dict, Any
from .orchestrator_types import ToolResult

class ToolContract:
    """
    Enforces inputs and outputs for a specific tool.
    (Future expansion: Add input validation schemas here).
    """
    @staticmethod
    def wrap_result(
        agent_name: str, 
        success: bool = True, 
        data: Dict[str, Any] = None, 
        message: str = "", 
        error: str = None,
        latency: int = 0,
        tokens: int = 0
    ) -> ToolResult:
        return ToolResult(
            success=success,
            data=data or {},
            message=message,
            error=error,
            agent=agent_name,
            latency_ms=latency,
            total_tokens=tokens,
            retryable=error is not None # Basic heuristic
        )
