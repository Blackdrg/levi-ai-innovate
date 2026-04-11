"""
Sovereign Calculation & Logic Engine v8.
Safely executes Python code in a restricted local environment.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
import asyncio
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class PythonInput(BaseModel):
    code: str = Field(..., description="The Python code to execute")
    timeout: int = 5

class PythonReplAgent(SovereignAgent[PythonInput, AgentResult]):
    """
    Sovereign Python REPL.
    Executes restricted Python code for calculation, logic, and data analysis missions.
    """
    
    def __init__(self):
        super().__init__("PythonREPL")

    async def _run(self, input_data: PythonInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Execution Protocol v14.2 (Hardened Docker Sandbox):
        1. Multi-layer Isolation (gVisor ready).
        2. Strict Resource Limiting.
        3. No Network Access.
        4. PII Redaction Filter.
        """
        from backend.core.executor.sandbox import get_sandbox
        from backend.utils.sanitizer import ResultSanitizer
        
        agent_config = kwargs.get("agent_config")
        sandbox = get_sandbox(agent_config)
        
        code = input_data.code
        self.logger.info(f"Executing Isolated Logic Mission ({sandbox.__class__.__name__}): {code[:50]}...")
        
        # 1. Execute in Sandbox
        result = await sandbox.run_code(code)
        
        # 2. PII Redaction (Wiring #3)
        stdout = ResultSanitizer.redact_pii(result.get("stdout", ""))
        stderr = ResultSanitizer.redact_pii(result.get("stderr", ""))
        
        message = stdout if result["success"] else f"Execution Error: {stderr}"
        
        return {
            "success": result["success"],
            "message": message,
            "data": {
                "sandbox_id": result.get("sandbox_id"),
                "exit_code": 0 if result["success"] else 1
            }
        }
